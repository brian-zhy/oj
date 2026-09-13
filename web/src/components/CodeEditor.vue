<script setup lang="ts">
/**
 * 代码编辑器 / 只读代码查看器（CodeMirror 6）
 *
 * 对外契约与之前的 Monaco 版本完全一致：
 *   props: modelValue / language / readonly / height
 *   emit : update:modelValue
 * 因此两个调用方（ProblemSubmit / SubmissionDetail）无需改用法。
 */
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { Compartment, EditorState } from '@codemirror/state'
import {
  EditorView,
  drawSelection,
  dropCursor,
  highlightActiveLine,
  highlightActiveLineGutter,
  highlightSpecialChars,
  keymap,
  lineNumbers,
} from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { bracketMatching, indentOnInput, indentUnit } from '@codemirror/language'
import { closeBrackets, closeBracketsKeymap, completionKeymap } from '@codemirror/autocomplete'
import { cpp } from '@codemirror/lang-cpp'
import { python } from '@codemirror/lang-python'
import { languages as langData } from '@codemirror/language-data'
import { oneDark } from '@codemirror/theme-one-dark'
import { copyText } from '@/utils/codeCopy'

interface Props {
  modelValue: string
  language: string
  readonly?: boolean
  height?: string
  /** 是否显示「载入文件」按钮（只读模式下忽略） */
  loadable?: boolean
  /** 载入文件时的字符上限，超出则拒绝载入（0 表示不限制） */
  maxChars?: number
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  height: '400px',
  loadable: false,
  maxChars: 0,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'load', payload: { name: string; chars: number }): void
  (e: 'load-error', message: string): void
}>()

const host = ref<HTMLDivElement | null>(null)
const view = shallowRef<EditorView | null>(null)
const copied = ref(false)
let copiedTimer: ReturnType<typeof setTimeout> | undefined

// 语言与只读状态都可能运行期变化，用 Compartment 做局部重配置
const langCompartment = new Compartment()
const readonlyCompartment = new Compartment()

const readonlyExtensions = (ro: boolean) =>
  ro ? [EditorState.readOnly.of(true), EditorView.editable.of(false)] : []

/** 常用语言直接映射；其余交给 @codemirror/language-data 按名字/别名匹配 */
async function resolveLanguage(name: string) {
  const key = (name || '').toLowerCase()
  if (key === 'cpp' || key === 'c' || key === 'c++') return cpp()
  if (key === 'python' || key === 'python3') return python()

  const desc = langData.find(
    (d) => d.name.toLowerCase() === key || d.alias.includes(key),
  )
  if (desc) {
    try {
      return await desc.load()
    } catch {
      /* 加载失败则退回纯文本 */
    }
  }
  return []
}

onMounted(async () => {
  const language = await resolveLanguage(props.language)

  const state = EditorState.create({
    doc: props.modelValue,
    extensions: [
      lineNumbers(),
      highlightActiveLineGutter(),
      highlightActiveLine(),
      highlightSpecialChars(),
      history(),
      drawSelection(),
      dropCursor(),
      EditorState.allowMultipleSelections.of(true),
      EditorView.lineWrapping,
      indentOnInput(),
      indentUnit.of('  '),
      EditorState.tabSize.of(2),
      bracketMatching(),
      closeBrackets(),
      // oneDark 已同时包含主题与语法配色，无需再单独 syntaxHighlighting(...)
      oneDark,
      langCompartment.of(language),
      readonlyCompartment.of(readonlyExtensions(props.readonly)),
      keymap.of([
        indentWithTab,
        ...closeBracketsKeymap,
        ...defaultKeymap,
        ...historyKeymap,
        ...completionKeymap,
      ]),
      EditorView.updateListener.of((u) => {
        if (u.docChanged) emit('update:modelValue', u.state.doc.toString())
      }),
      EditorView.theme({
        '&': {
          height: '100%',
          fontSize: '14px',
        },
        // 注意：CodeMirror 基础样式会直接在 .cm-content 上设 font-family，
        // 只写在 '&' 上会被它盖掉（直接规则永远优先于继承），所以必须写在这里。
        '.cm-content': {
          fontFamily: '"JetBrains Mono", "Fira Code", Consolas, Monaco, monospace',
        },
        '&.cm-focused': { outline: 'none' },
        '.cm-scroller': {
          overflow: 'auto',
          lineHeight: '1.6',
          fontFamily: '"JetBrains Mono", "Fira Code", Consolas, Monaco, monospace',
        },
      }),
    ],
  })

  view.value = new EditorView({ state, parent: host.value! })
})

// 外部值变化（如详情页异步拿到提交内容）
watch(
  () => props.modelValue,
  (val) => {
    const v = view.value
    if (!v) return
    const cur = v.state.doc.toString()
    const next = val ?? ''
    if (cur === next) return
    v.dispatch({ changes: { from: 0, to: cur.length, insert: next } })
  },
)

// 语言切换
watch(
  () => props.language,
  async (lang) => {
    const v = view.value
    if (!v) return
    const ext = await resolveLanguage(lang)
    v.dispatch({ effects: langCompartment.reconfigure(ext) })
  },
)

// 只读切换
watch(
  () => props.readonly,
  (ro) => {
    view.value?.dispatch({
      effects: readonlyCompartment.reconfigure(readonlyExtensions(ro)),
    })
  },
)

async function handleCopy() {
  const ok = await copyText(props.modelValue ?? '')
  copied.value = ok
  clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => {
    copied.value = false
  }, 1600)
}

/* ---------------- 载入本地文件 ---------------- */

const ACCEPT =
  '.c,.cc,.cpp,.cxx,.h,.hh,.hpp,.hxx,.py,.py3,.java,.js,.ts,.go,.rs,.pas,.txt'
const MAX_FILE_BYTES = 5 * 1024 * 1024

const fileInput = ref<HTMLInputElement | null>(null)

function pickFile() {
  fileInput.value?.click()
}

/**
 * 解码文件内容。
 * 浏览器默认按 UTF-8 解码，但 Windows 下保存的 .cpp 常见 GBK/GB2312 编码，
 * 当 UTF-8 读会变乱码 —— 以替换字符 U+FFFD 作为判定信号，再试中文编码。
 */
async function decodeFile(file: File): Promise<string> {
  const buf = await file.arrayBuffer()
  const utf8 = new TextDecoder('utf-8').decode(buf)
  if (!utf8.includes('\uFFFD')) return utf8

  // gb18030 是 GBK/GB2312 的超集，big5 覆盖繁体中文
  for (const enc of ['gb18030', 'big5']) {
    try {
      const text = new TextDecoder(enc).decode(buf)
      if (!text.includes('\uFFFD')) return text
    } catch {
      /* 浏览器不支持该编码标签，继续尝试下一个 */
    }
  }
  return utf8
}

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  // 复位，保证连续选择同一个文件也能再次触发 change
  input.value = ''
  if (!file) return

  if (file.size > MAX_FILE_BYTES) {
    emit('load-error', `文件过大（${(file.size / 1024 / 1024).toFixed(1)} MB），最多 5 MB`)
    return
  }

  try {
    const text = await decodeFile(file)
    const limit = props.maxChars
    if (limit > 0 && text.length > limit) {
      emit('load-error', `文件内容 ${text.length} 字符，超过上限 ${limit} 字符`)
      return
    }
    const v = view.value
    if (!v) return
    // 走 dispatch，updateListener 会自动 emit update:modelValue
    v.dispatch({ changes: { from: 0, to: v.state.doc.length, insert: text } })
    v.focus()
    emit('load', { name: file.name, chars: text.length })
  } catch {
    emit('load-error', '读取文件失败')
  }
}

onBeforeUnmount(() => {
  clearTimeout(copiedTimer)
  view.value?.destroy()
  view.value = null
})
</script>

<template>
  <div class="code-editor" :style="{ height }">
    <div ref="host" class="ce-host" />

    <div v-if="(loadable && !readonly) || modelValue" class="ce-tools">
      <button
        v-if="loadable && !readonly"
        type="button"
        class="ce-btn"
        title="从本地文件载入代码"
        @click="pickFile"
      >
        <i class="fa-solid fa-folder-open" />
        <span>载入文件</span>
      </button>
      <button
        v-if="modelValue"
        type="button"
        class="ce-btn"
        :class="{ copied }"
        :title="copied ? '已复制' : '复制代码'"
        @click="handleCopy"
      >
        <i :class="copied ? 'fa-solid fa-check' : 'fa-solid fa-copy'" />
        <span>{{ copied ? '已复制' : '复制' }}</span>
      </button>
    </div>

    <input
      ref="fileInput"
      type="file"
      class="ce-file"
      :accept="ACCEPT"
      @change="onFileChange"
    />
  </div>
</template>

<style scoped>
.code-editor {
  position: relative;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  overflow: hidden;
  /* oneDark 的底色，避免编辑器初始化瞬间闪白 */
  background: #282c34;
}

.ce-host {
  height: 100%;
}

/* 右上角工具组：载入文件 / 复制 */
.ce-tools {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 6px;
}

.ce-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  font-size: 11px;
  line-height: 16px;
  color: #abb2bf;
  background-color: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 5px;
  cursor: pointer;
  opacity: 0.75;
  transition: opacity 0.15s, background-color 0.15s, color 0.15s;
}

.ce-btn:hover {
  opacity: 1;
  color: #fff;
  background-color: rgba(255, 255, 255, 0.18);
}

.ce-btn.copied {
  opacity: 1;
  color: #98c379;
  border-color: rgba(152, 195, 121, 0.45);
}

/* 原生 file input 只作为触发器，不显示 */
.ce-file {
  display: none;
}
</style>
