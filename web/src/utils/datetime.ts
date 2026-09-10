/** 格式化后端返回的 ISO 时间串为本地时区的 "YYYY-MM-DD HH:MM"。
 *
 * 后端（Postgres timestamptz）返回的是 UTC ISO 串（带 +00:00 后缀），
 * 直接对字符串切割不做时区转换会与北京时间差 8 小时，
 * 必须经 Date 解析后取本地时间字段。
 */
export const fmtDateTime = (
  iso: string | null | undefined,
  fallback = '—',
): string => {
  if (!iso) return fallback
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
