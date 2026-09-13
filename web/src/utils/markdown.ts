import katex from 'katex'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import cpp from 'highlight.js/lib/languages/cpp'
import c from 'highlight.js/lib/languages/c'
import python from 'highlight.js/lib/languages/python'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import bash from 'highlight.js/lib/languages/bash'
import plaintext from 'highlight.js/lib/languages/plaintext'
import 'katex/dist/katex.min.css'

// 按需注册语言，避免把 highlight.js 的全量语言包打进来
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('c', c)
hljs.registerLanguage('python', python)
hljs.registerLanguage('java', java)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('plaintext', plaintext)

// 换行即换行（与聊天/犇犇的书写习惯一致），启用 GFM（表格/删除线/任务列表）
marked.setOptions({ breaks: true, gfm: true })

/** 代码围栏的语言标记 → highlight.js 语言名 */
const FENCE_LANG: Record<string, string> = {
  cpp: 'cpp', 'c++': 'cpp', cc: 'cpp', cxx: 'cpp', 'c++14': 'cpp', 'c++17': 'cpp',
  c: 'c',
  python: 'python', py: 'python', python3: 'python',
  java: 'java',
  javascript: 'javascript', js: 'javascript', node: 'javascript',
  bash: 'bash', sh: 'bash', shell: 'bash', zsh: 'bash',
  text: 'plaintext', txt: 'plaintext', plaintext: 'plaintext',
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/**
 * 渲染一个围栏代码块：语法高亮 + 右上角复制按钮。
 * 未标注语言或语言不在注册表内时按纯文本处理（不做自动检测，
 * 因为实时预览会频繁重渲染，highlightAuto 太慢）。
 *
 * 复制按钮的点击由 utils/codeCopy.ts 的全局委托处理 —— v-html 内容无法绑定事件。
 */
function renderCodeBlock(info: string, body: string): string {
  const raw = body.replace(/\n$/, '')
  const key = info.trim().toLowerCase()
  const lang = FENCE_LANG[key]
  let inner = escapeHtml(raw)
  if (lang) {
    try {
      inner = hljs.highlight(raw, { language: lang, ignoreIllegals: true }).value
    } catch {
      inner = escapeHtml(raw)
    }
  }
  const cls = lang ? `hljs language-${lang}` : 'hljs'
  // 语言标签展示作者写的原始标记（如 c++14）；截断长度避免撑破布局
  const label = key ? `<span class="code-lang">${escapeHtml(key.slice(0, 16))}</span>` : ''
  return (
    '<div class="code-block">' +
    `<div class="code-tools">${label}` +
    '<button type="button" class="code-copy" data-copy>' +
    '<i class="fa-solid fa-copy"></i><span data-copy-label>复制</span>' +
    '</button></div>' +
    `<pre><code class="${cls}">${inner}</code></pre>` +
    '</div>'
  )
}

function katexHtml(tex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(tex.trim(), { throwOnError: false, displayMode })
  } catch {
    return escapeHtml(tex)
  }
}

/**
 * 富文本渲染：完整 Markdown（marked + DOMPurify）+ KaTeX 数学公式
 * - 行内公式：$E = mc^2$
 * - 块级公式：$$\int_0^1 x\,dx$$
 * - 标题 / 列表 / 表格 / 引用 / 代码块 / 行内代码 / 链接 / 图片 / 删除线 / @提及
 */
export function renderRichText(content: string): string {
  if (!content) return ''

  // 每次渲染生成随机标记（正文不可能自然出现，杜绝占位符与内容冲突）
  const uid = Math.random().toString(36).slice(2, 10)
  const CODE_MARK = 'K' + uid + 'c'
  const MATH_MARK = 'K' + uid + 'm'

  const codeBlocks: string[] = []
  const displayMath: string[] = []

  // 1. 代码块与行内代码先占位（保护内部的 $ 与 Markdown 符号）
  //    捕获组说明：第 1 组是围栏后的语言标记，第 2 组才是代码正文。
  //    旧写法把语言标记也当成了代码内容，预览里会多出一行 "cpp"。
  content = content.replace(
    /```([^\n`]*)\n([\s\S]*?)\n?```/g,
    (_, info: string, body: string) => {
      const idx = codeBlocks.length
      codeBlocks.push(renderCodeBlock(info, body))
      return CODE_MARK + idx + CODE_MARK
    },
  )
  content = content.replace(/`([^`\n]+)`/g, (_, code: string) => {
    const idx = codeBlocks.length
    codeBlocks.push('<code>' + escapeHtml(code) + '</code>')
    return CODE_MARK + idx + CODE_MARK
  })

  // 2. LaTeX 公式占位（块级 $$...$$ 与行内 $...$）
  content = content.replace(/\$\$([\s\S]+?)\$\$/g, (_, tex: string) => {
    const idx = displayMath.length
    displayMath.push(katexHtml(tex, true))
    return MATH_MARK + idx + MATH_MARK
  })
  content = content.replace(/\$([^$\n]+?)\$/g, (_, tex: string) => {
    const idx = displayMath.length
    displayMath.push(katexHtml(tex, false))
    return MATH_MARK + idx + MATH_MARK
  })

  // 3. marked 解析标准 Markdown
  let html = marked.parse(content) as string

  // 4. DOMPurify 消毒（随机标记原样保留）
  html = DOMPurify.sanitize(html)

  // 5. 还原公式占位（KaTeX 输出自身安全）
  html = html.replace(new RegExp(MATH_MARK + '(\\d+)' + MATH_MARK, 'g'), (_, i: string) => displayMath[+i] ?? '')

  // 6. 还原代码占位。先吃掉标记外层的 <p>，否则每个代码块前后都会多出空段落
  html = html
    .replace(
      new RegExp('<p>\\s*' + CODE_MARK + '(\\d+)' + CODE_MARK + '\\s*</p>', 'g'),
      (_, i: string) => codeBlocks[+i] ?? '',
    )
    .replace(new RegExp(CODE_MARK + '(\\d+)' + CODE_MARK, 'g'), (_, i: string) => codeBlocks[+i] ?? '')

  return html
}
