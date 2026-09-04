import katex from 'katex'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import 'katex/dist/katex.min.css'

// 换行即换行（与聊天/犇犇的书写习惯一致），启用 GFM（表格/删除线/任务列表）
marked.setOptions({ breaks: true, gfm: true })

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function katexHtml(tex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(tex.trim(), { throwOnError: false, displayMode })
  } catch {
    return escapeHtml(tex)
  }
}

// 内部占位符（控制字符包裹下标，正文中不可能自然出现）
const CODE_MARK = ''
const MATH_MARK = ''

/**
 * 富文本渲染：完整 Markdown（marked + DOMPurify）+ KaTeX 数学公式
 * - 行内公式：$E = mc^2$
 * - 块级公式：$$\int_0^1 x\,dx$$
 * - 标题 / 列表 / 表格 / 引用 / 代码块 / 行内代码 / 链接 / 图片 / 删除线 / @提及
 */
export function renderRichText(content: string): string {
  if (!content) return ''

  const codeBlocks: string[] = []
  const displayMath: string[] = []

  // 1. 代码块与行内代码先占位（保护内部的 $ 与 Markdown 符号）
  content = content.replace(/```([\s\S]*?)```/g, (_, code: string) => {
    const idx = codeBlocks.length
    codeBlocks.push('<pre><code>' + escapeHtml(code) + '</code></pre>')
    return CODE_MARK + idx + CODE_MARK
  })
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

  // 4. DOMPurify 消毒（占位控制字符会原样保留）
  html = DOMPurify.sanitize(html)

  // 5. 还原公式占位（KaTeX 输出自身安全）
  html = html.replace(new RegExp(MATH_MARK + '(\\d+)' + MATH_MARK, 'g'), (_, i: string) => displayMath[+i] ?? '')

  // 6. 还原代码占位
  html = html.replace(new RegExp(CODE_MARK + '(\\d+)' + CODE_MARK, 'g'), (_, i: string) => codeBlocks[+i] ?? '')

  return html
}
