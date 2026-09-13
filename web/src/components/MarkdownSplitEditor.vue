<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { EditorSelection, EditorState, type ChangeSpec } from '@codemirror/state'
import { EditorView, keymap, placeholder as cmPlaceholder } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { defaultHighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { markdown, markdownLanguage } from '@codemirror/lang-markdown'
import { languages } from '@codemirror/language-data'
import { renderRichText } from '@/utils/markdown'

/**
 * Markdown 分栏编辑器（CodeMirror 6 编辑区 + 原有 marked 预览）
 *
 * 渲染仍走 @/utils/markdown 的 renderRichText，站内已有内容显示完全不变，
 * 本次只替换「编辑外壳」：语法高亮、工具栏、编写/分栏/预览切换、全屏。
 */
const props = withDefaults(
  defineProps<{
    modelValue: string
    placeholder?: string
    height?: string
    maxlength?: string | number
    /** 是否显示内置预览面板；ProblemEdit 自带预览，传 false 避免重复 */
    preview?: boolean
  }>(),
  { placeholder: '', height: '320px', maxlength: 0, preview: true },
)

const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const host = ref<HTMLDivElement | null>(null)
const viewRef = shallowRef<EditorView | null>(null)
const mode = ref<'write' | 'split' | 'preview'>('split')
const fullscreen = ref(false)
const hint = ref('')
const charCount = ref((props.modelValue || '').length)

let hintTimer: ReturnType<typeof setTimeout> | undefined
let previewTimer: ReturnType<typeof setTimeout> | undefined

/** maxlength 归一化：非正数视为不限制 */
const maxLen = computed(() => {
  const n = Number(props.maxlength)
  return Number.isFinite(n) && n > 0 ? n : 0
})

// 预览防抖：长题面（大量公式）连续输入时避免每次都跑 KaTeX
const previewSource = ref(props.modelValue || '')
watch(
  () => props.modelValue,
  (v) => {
    charCount.value = (v || '').length
    clearTimeout(previewTimer)
    previewTimer = setTimeout(() => {
      previewSource.value = v || ''
    }, 100)
  },
)
const previewHtml = computed(() => renderRichText(previewSource.value))

function showHint(msg: string) {
  hint.value = msg
  clearTimeout(hintTimer)
  hintTimer = setTimeout(() => {
    hint.value = ''
  }, 1800)
}

/* ---------------- 编辑命令 ---------------- */

/** 包裹选区（粗体/斜体/行内代码等） */
function wrap(view: EditorView, before: string, after: string, sample: string) {
  const { state } = view
  const spec = state.changeByRange((range) => {
    const text = state.sliceDoc(range.from, range.to) || sample
    return {
      changes: { from: range.from, to: range.to, insert: before + text + after },
      range: EditorSelection.range(
        range.from + before.length,
        range.from + before.length + text.length,
      ),
    }
  })
  view.dispatch(spec)
  view.focus()
}

/** 整块插入（代码块 / 块级公式） */
function wrapBlock(view: EditorView, before: string, after: string, sample: string) {
  const { state } = view
  const sel = state.selection.main
  const text = state.sliceDoc(sel.from, sel.to) || sample
  const padStart = sel.from === state.doc.lineAt(sel.from).from ? '' : '\n'
  const padEnd = sel.to === state.doc.lineAt(sel.to).to ? '' : '\n'
  const insert = padStart + before + text + after + padEnd
  const innerFrom = sel.from + padStart.length + before.length
  view.dispatch({
    changes: { from: sel.from, to: sel.to, insert },
    selection: { anchor: innerFrom, head: innerFrom + text.length },
  })
  view.focus()
}

/** 行首前缀切换（标题 / 引用 / 列表）：已全部带前缀则移除 */
function toggleLine(view: EditorView, prefix: string) {
  const { state } = view
  const sel = state.selection.main
  const start = state.doc.lineAt(sel.from)
  const end = state.doc.lineAt(sel.to)
  const lines = []
  for (let n = start.number; n <= end.number; n++) lines.push(state.doc.line(n))
  const remove = lines.every((l) => l.text.startsWith(prefix))
  const changes: ChangeSpec[] = lines.map((l) =>
    remove
      ? { from: l.from, to: l.from + prefix.length, insert: '' }
      : { from: l.from, insert: prefix },
  )
  view.dispatch({ changes })
  view.focus()
}

/** 插入链接，并把 URL 占位选中方便直接覆盖 */
function insertLink(view: EditorView) {
  const { state } = view
  const sel = state.selection.main
  const text = state.sliceDoc(sel.from, sel.to) || '链接文字'
  const urlFrom = sel.from + 1 + text.length + 2
  view.dispatch({
    changes: { from: sel.from, to: sel.to, insert: `[${text}](https://)` },
    selection: { anchor: urlFrom, head: urlFrom + 'https://'.length },
  })
  view.focus()
}

function insertText(view: EditorView, text: string) {
  const { state } = view
  const sel = state.selection.main
  view.dispatch({
    changes: { from: sel.from, to: sel.to, insert: text },
    selection: { anchor: sel.from + text.length },
  })
  view.focus()
}

interface Tool {
  icon: string
  title: string
  run: (view: EditorView) => void
}

const toolGroups: Tool[][] = [
  [
    { icon: 'fa-solid fa-bold', title: '粗体', run: (v) => wrap(v, '**', '**', '粗体') },
    { icon: 'fa-solid fa-italic', title: '斜体', run: (v) => wrap(v, '*', '*', '斜体') },
    { icon: 'fa-solid fa-strikethrough', title: '删除线', run: (v) => wrap(v, '~~', '~~', '删除线') },
  ],
  [
    { icon: 'fa-solid fa-heading', title: '标题', run: (v) => toggleLine(v, '## ') },
    { icon: 'fa-solid fa-quote-left', title: '引用', run: (v) => toggleLine(v, '> ') },
    { icon: 'fa-solid fa-list-ul', title: '无序列表', run: (v) => toggleLine(v, '- ') },
    { icon: 'fa-solid fa-list-ol', title: '有序列表', run: (v) => toggleLine(v, '1. ') },
  ],
  [
    { icon: 'fa-solid fa-code', title: '行内代码', run: (v) => wrap(v, '`', '`', 'code') },
    { icon: 'fa-solid fa-file-code', title: '代码块', run: (v) => wrapBlock(v, '```\n', '\n```', '代码') },
    { icon: 'fa-solid fa-link', title: '链接', run: insertLink },
  ],
  [
    { icon: 'fa-solid fa-square-root-variable', title: '行内公式', run: (v) => wrap(v, '$', '$', 'E=mc^2') },
    { icon: 'fa-solid fa-superscript', title: '块级公式', run: (v) => wrapBlock(v, '$$\n', '\n$$', '\\int_0^1 x\\,dx') },
    { icon: 'fa-solid fa-minus', title: '分割线', run: (v) => insertText(v, '\n---\n') },
  ],
]

function runTool(t: Tool) {
  const v = viewRef.value
  if (v) t.run(v)
}

/* ---------------- 视图状态 ---------------- */

function setMode(m: 'write' | 'split' | 'preview') {
  mode.value = m
  // 面板 display 变化后需要重新测量，否则 CodeMirror 尺寸会错乱
  nextTick(() => viewRef.value?.requestMeasure())
}

function toggleFullscreen() {
  fullscreen.value = !fullscreen.value
  document.body.style.overflow = fullscreen.value ? 'hidden' : ''
  nextTick(() => viewRef.value?.requestMeasure())
}

/* ---------------- 编辑器初始化 ---------------- */

const cmTheme = EditorView.theme(
  {
    '&': { height: '100%', fontSize: '13px', backgroundColor: '#fff', color: '#2d3748' },
    '&.cm-focused': { outline: 'none' },
    '.cm-scroller': {
      fontFamily: "Consolas, Monaco, 'Courier New', monospace",
      lineHeight: '1.6',
      overflow: 'auto',
    },
    '.cm-content': { padding: '10px 12px', caretColor: '#2d3748' },
    '.cm-line': { padding: '0' },
    '.cm-placeholder': { color: '#b6c0cd' },
  },
  { dark: false },
)

onMounted(() => {
  const state = EditorState.create({
    doc: props.modelValue || '',
    extensions: [
      history(),
      EditorView.lineWrapping,
      markdown({ base: markdownLanguage, codeLanguages: languages }),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      keymap.of([
        { key: 'Mod-b', run: (v) => (wrap(v, '**', '**', '粗体'), true) },
        { key: 'Mod-i', run: (v) => (wrap(v, '*', '*', '斜体'), true) },
        { key: 'Mod-k', run: (v) => (insertLink(v), true) },
        indentWithTab,
        ...defaultKeymap,
        ...historyKeymap,
      ]),
      EditorView.updateListener.of((u) => {
        if (!u.docChanged) return
        const limit = maxLen.value
        if (limit && u.state.doc.length > limit) {
          // 超限：截断到上限并提示（截断后长度等于上限，不会再次触发）
          u.view.dispatch({ changes: { from: limit, to: u.state.doc.length, insert: '' } })
          showHint(`已达 ${limit} 字上限`)
          return
        }
        emit('update:modelValue', u.state.doc.toString())
      }),
      cmTheme,
      props.placeholder ? cmPlaceholder(props.placeholder) : [],
    ],
  })
  viewRef.value = new EditorView({ state, parent: host.value! })
})

onBeforeUnmount(() => {
  clearTimeout(hintTimer)
  clearTimeout(previewTimer)
  document.body.style.overflow = ''
  viewRef.value?.destroy()
  viewRef.value = null
})

// 父组件从外部改动内容（如打开编辑框回填）时同步到编辑器
watch(
  () => props.modelValue,
  (val) => {
    const view = viewRef.value
    if (!view) return
    const cur = view.state.doc.toString()
    const next = val || ''
    if (cur === next) return
    const anchor = Math.min(view.state.selection.main.from, next.length)
    view.dispatch({
      changes: { from: 0, to: cur.length, insert: next },
      selection: { anchor },
    })
  },
)

// 供父组件聚焦；返回内部可聚焦元素（保持原有对外契约）
const focus = (): HTMLElement | null => {
  viewRef.value?.focus()
  return viewRef.value?.contentDOM ?? null
}
defineExpose({ focus })
</script>

<template>
  <div class="mde" :class="{ 'is-fullscreen': fullscreen }">
    <div class="mde-toolbar">
      <template v-for="(group, gi) in toolGroups" :key="gi">
        <span v-if="gi > 0" class="tb-sep" />
        <button
          v-for="t in group"
          :key="t.title"
          type="button"
          class="tb-btn"
          :title="t.title"
          :aria-label="t.title"
          @click="runTool(t)"
        >
          <i :class="t.icon" />
        </button>
      </template>

      <span class="tb-spacer" />

      <span v-if="maxLen" class="tb-count" :class="{ over: charCount >= maxLen }">
        {{ charCount }} / {{ maxLen }}
      </span>

      <div v-if="preview" class="tb-group">
        <button
          type="button"
          class="tb-btn"
          :class="{ active: mode === 'write' }"
          title="仅编写"
          @click="setMode('write')"
        >
          <i class="fa-solid fa-pen" />
        </button>
        <button
          type="button"
          class="tb-btn"
          :class="{ active: mode === 'split' }"
          title="分栏预览"
          @click="setMode('split')"
        >
          <i class="fa-solid fa-table-columns" />
        </button>
        <button
          type="button"
          class="tb-btn"
          :class="{ active: mode === 'preview' }"
          title="仅预览"
          @click="setMode('preview')"
        >
          <i class="fa-solid fa-eye" />
        </button>
      </div>

      <button
        type="button"
        class="tb-btn"
        :title="fullscreen ? '退出全屏' : '全屏'"
        @click="toggleFullscreen"
      >
        <i :class="fullscreen ? 'fa-solid fa-compress' : 'fa-solid fa-expand'" />
      </button>
    </div>

    <div
      class="mde-body"
      :class="{ fill: fullscreen }"
      :style="fullscreen ? undefined : { height: props.height || '320px' }"
    >
      <div class="mde-pane mde-write" :class="{ hidden: preview && mode === 'preview' }">
        <div ref="host" class="mde-cm" />
      </div>
      <div
        v-if="preview"
        class="mde-pane mde-preview prose"
        :class="{ hidden: mode === 'write' }"
        v-html="previewHtml"
      />
    </div>

    <div v-if="hint" class="mde-hint">{{ hint }}</div>
  </div>
</template>

<style scoped>
.mde {
  position: relative;
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  border: 1px solid #dce0e6;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.mde.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 3000;
  border: none;
  border-radius: 0;
}

/* ---------- 工具栏 ---------- */
.mde-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 5px 8px;
  background: #fafbfc;
  border-bottom: 1px solid #eef1f5;
}

.tb-sep {
  width: 1px;
  height: 16px;
  background: #e3e8ef;
  margin: 0 3px;
}

.tb-spacer { flex: 1; }

.tb-btn {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 5px;
  color: #607089;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.tb-btn:hover { background: #eaeef4; color: #2d3748; }
.tb-btn.active { background: #e3edff; color: #2563eb; }

.tb-group {
  display: flex;
  gap: 2px;
  padding: 2px;
  border-radius: 6px;
  background: #f0f3f7;
}

.tb-count {
  font-size: 11px;
  color: #96a2b4;
  margin: 0 4px;
  white-space: nowrap;
}

.tb-count.over { color: #dc2626; font-weight: 600; }

/* ---------- 编辑区 / 预览区 ---------- */
.mde-body { display: flex; min-height: 0; }
.mde-body.fill { flex: 1 1 auto; }

.mde-pane {
  flex: 1 1 0;
  /* 关键：不加 min-height:0 时 flex 子项会被内容撑高，预览区无法内部滚动 */
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mde-pane.hidden { display: none; }

/* CodeMirror 挂载点 */
.mde-cm { flex: 1; min-height: 0; }

.mde-preview {
  overflow-y: auto;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.7;
  color: #2d3748;
  word-break: break-word;
  border-left: 1px solid #eef1f5;
}

/* ---------- 超限提示 ---------- */
.mde-hint {
  position: absolute;
  right: 12px;
  bottom: 10px;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(30, 41, 59, 0.9);
  color: #fff;
  font-size: 12px;
  pointer-events: none;
}

@media (max-width: 760px) {
  .mde-body { flex-direction: column; height: auto !important; }
  .mde-pane { flex: none; }
  .mde-write { height: 220px; }
  .mde-preview {
    max-height: 320px;
    border-left: none;
    border-top: 1px solid #eef1f5;
  }
}
</style>
