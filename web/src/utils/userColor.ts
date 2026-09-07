// 用户名配色（全站统一）：
// - 封禁 → 灰
// - 作弊者 → 棕
// - 进入后台（is_admin / is_super_admin）→ 紫
// - 有管理权限但未进后台（用户/秩序/题目管理）→ 青 #13C2C2
// - 普通用户 → 红
export const COLOR_BANNED = '#95a5a6'
export const COLOR_CHEATER = '#AD8B00'
export const COLOR_ADMIN = '#9C3DCF'
export const COLOR_MODERATOR = '#13C2C2'
export const COLOR_DEFAULT = '#e74c3c'

export function userNameColor(user: any): string {
  if (!user) return COLOR_DEFAULT
  if (user.is_banned) return COLOR_BANNED
  if (user.is_cheater) return COLOR_CHEATER
  if (user.is_admin || user.is_super_admin) return COLOR_ADMIN
  if (user.can_manage_users || user.can_manage_posts || user.can_manage_problems) {
    return COLOR_MODERATOR
  }
  return COLOR_DEFAULT
}
