/**
 * 剪贴板与「复制代码」按钮的全局支持。
 *
 * 为什么需要全局委托：Markdown 代码块是通过 v-html 插入的，
 * Vue 无法给里面的按钮绑定 @click，所以统一在 document 上做事件委托。
 */

/** 复制文本到剪贴板，返回是否成功 */
export async function copyText(text: string): Promise<boolean> {
  // 首选异步剪贴板 API —— 但它要求安全上下文（HTTPS 或 localhost），
  // 本站线上是 http://服务器IP/，所以必须保留 execCommand 回退。
  if (window.isSecureContext && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      /* 权限被拒等情况，落到回退方案 */
    }
  }

  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    // 固定定位 + 移出视口，避免触发页面滚动
    ta.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0'
    document.body.appendChild(ta)
    ta.select()
    ta.setSelectionRange(0, ta.value.length)
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}

const COPIED_RESET_MS = 1600

/**
 * 安装全局复制按钮委托。
 * 约定：任何带 data-copy 的按钮，点击后复制其所在
 * .code-block / .code-wrap 容器内 <pre> 的纯文本。
 */
export function installCodeCopy(): void {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement | null
    const btn = target?.closest?.('[data-copy]') as HTMLElement | null
    if (!btn) return

    const host = btn.closest('.code-block, .code-wrap')
    const pre = host?.querySelector('pre')
    if (!pre) return

    e.preventDefault()
    void (async () => {
      const ok = await copyText(pre.textContent ?? '')
      // 按钮里可能还有图标，只替换文字标签，避免把图标一并清掉
      const label = (btn.querySelector('[data-copy-label]') as HTMLElement | null) ?? btn
      const restore = label.textContent ?? '复制'
      label.textContent = ok ? '已复制' : '复制失败'
      btn.classList.toggle('is-copied', ok)
      window.setTimeout(() => {
        label.textContent = restore
        btn.classList.remove('is-copied')
      }, COPIED_RESET_MS)
    })()
  })
}
