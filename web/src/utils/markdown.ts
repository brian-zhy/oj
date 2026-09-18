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

/**
 * 用户 Markdown 转成 HTML 后使用的严格白名单。
 *
 * 这里不能只依赖 DOMPurify 的默认配置：默认配置允许 style/class/id，
 * 恶意用户可以借此插入 fixed/absolute 的大尺寸遮罩，即使没有脚本也能
 * 覆盖首页。代码块和公式使用占位符保护，因此这里处理的只有用户内容。
 */
const USER_HTML_CONFIG = {
  ALLOWED_TAGS: [
    'a', 'b', 'blockquote', 'br', 'code', 'del', 'em', 'h1', 'h2', 'h3',
    'h4', 'h5', 'h6', 'hr', 'i', 'img', 'li', 'ol', 'p', 'pre', 's',
    'strong', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'u',
    'ul',
  ],
  ALLOWED_ATTR: ['alt', 'href', 'rel', 'src', 'target', 'title'],
  ALLOW_DATA_ATTR: false,
  FORBID_ATTR: ['class', 'id', 'style'],
  FORBID_TAGS: [
    'embed', 'form', 'iframe', 'input', 'link', 'meta', 'object', 'script',
    'style', 'svg', 'template', 'textarea', 'video', 'audio',
  ],
  // 只允许普通网页链接和站内相对链接，拒绝 javascript:/data: 等协议。
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|\/|#)/i,
}

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

// 用户名规则见 service/app/schemas/user.py：^[A-Za-z0-9_]{3,50}$
// 前面不能是单词字符、点或斜杠：单词字符/点避开邮箱（a@b.com），
// 斜杠避开链接路径（https://x.com/@foo）。
// 后端 app/services/notification.py 用的是同一条规则，两边要保持一致
const MENTION_G = /(?<![\w./])@([A-Za-z0-9_]{3,50})/g
const MENTION_T = /(?<![\w./])@[A-Za-z0-9_]{3,50}/

/**
 * 把 @username 变成指向用户主页的链接。
 *
 * 走 DOM 文本节点而不是字符串替换：
 *   1. 字符串替换会把 `[x](https://a.com/@foo)` 这类链接地址里的 @ 也换掉；
 *   2. 无法避开 <a> / <code> / <pre> 内部（a 里再套 a 是非法结构）；
 *   3. 属性值必须原样不动。
 */
function linkifyMentions(html: string): string {
  if (!MENTION_T.test(html)) return html
  const root = document.createElement('div')
  root.innerHTML = html

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const targets: Text[] = []
  let node = walker.nextNode() as Text | null
  while (node) {
    const parent = node.parentElement
    if (parent && MENTION_T.test(node.nodeValue || '') && !parent.closest('a, code, pre')) {
      targets.push(node)
    }
    node = walker.nextNode() as Text | null
  }

  for (const textNode of targets) {
    const text = textNode.nodeValue || ''
    const frag = document.createDocumentFragment()
    let last = 0
    let m: RegExpExecArray | null
    MENTION_G.lastIndex = 0
    while ((m = MENTION_G.exec(text)) !== null) {
      if (m.index > last) {
        frag.appendChild(document.createTextNode(text.slice(last, m.index)))
      }
      const a = document.createElement('a')
      a.className = 'mention'
      a.setAttribute('href', `/user/${m[1]}`)
      a.textContent = '@' + m[1]
      frag.appendChild(a)
      last = m.index + m[0].length
    }
    if (last < text.length) {
      frag.appendChild(document.createTextNode(text.slice(last)))
    }
    textNode.parentNode?.replaceChild(frag, textNode)
  }

  return root.innerHTML
}

/**
 * 纯文本场景（工单回复、通知文案）的 @提及 渲染：转义后只把 @名字 变成链接。
 * 通知文案里写的就是 `@solver 回复了你的帖子`，这样用户名也能点。
 */
export function renderMentionText(content: string | null | undefined): string {
  if (!content) return ''
  return linkifyMentions(escapeHtml(content).replace(/\n/g, '<br>'))
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

  // 4. 先严格消毒用户可控的 HTML。
  //    这一步发生在还原代码/公式之前，避免为了支持 KaTeX 和复制按钮而
  //    放宽规则，导致用户 HTML 获得 style/class 等布局能力。
  html = DOMPurify.sanitize(html, USER_HTML_CONFIG)

  // 4.5 @提及 → 用户主页链接。放在这一步是为了让代码块/公式
  //     内部的 @ 还能被占位符保护住（那些占位符要到第 6 步才还原）
  html = linkifyMentions(html)

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
