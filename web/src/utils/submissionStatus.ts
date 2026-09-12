// 评测状态 → 中文文案与颜色（全站统一）
export const SUBMISSION_STATUS: Record<string, { text: string; color: string }> = {
  pending: { text: '待评测', color: '#909399' },
  judging: { text: '评测中', color: '#3498db' },
  accepted: { text: 'Accepted', color: '#52c41a' },
  wrong_answer: { text: 'Wrong Answer', color: '#e74c3c' },
  time_limit_exceeded: { text: 'Time Limit Exceeded', color: '#f39c11' },
  memory_limit_exceeded: { text: 'Memory Limit Exceeded', color: '#9d3dcf' },
  runtime_error: { text: 'Runtime Error', color: '#e67e22' },
  compile_error: { text: 'Compile Error', color: '#8a9aa8' },
  system_error: { text: 'System Error', color: '#0e1d69' },
}

export function submissionStatusText(s: string): string {
  return SUBMISSION_STATUS[s]?.text ?? s
}

export function submissionStatusColor(s: string): string {
  return SUBMISSION_STATUS[s]?.color ?? '#909399'
}

// 测试点状态 → 文案
export function caseStatusText(s: string): string {
  const map: Record<string, string> = {
    accepted: '通过',
    wrong_answer: '答案错误',
    time_limit_exceeded: '超时',
    memory_limit_exceeded: '内存超限',
    runtime_error: '运行错误',
    system_error: '系统错误',
  }
  return map[s] ?? s
}

// 题库列表：当前用户对某题的完成状态 → Font Awesome 图标 / 颜色 / 提示文案
// 图标需与 index.html 引入的 Font Awesome 6 匹配（<i class="...">）
export const PROBLEM_USER_STATUS: Record<
  string,
  { icon: string; color: string; text: string }
> = {
  accepted: {
    icon: 'fa-solid fa-circle-check',
    color: '#52c41a',
    text: '已通过',
  },
  attempted: {
    icon: 'fa-solid fa-circle-xmark',
    color: '#e74c3c',
    text: '尝试过，未通过',
  },
}

const PROBLEM_USER_STATUS_NONE = {
  icon: 'fa-regular fa-circle',
  color: '#c8d0d8',
  text: '未提交',
}

export function problemUserStatusMeta(status?: string | null) {
  return PROBLEM_USER_STATUS[status ?? ''] ?? PROBLEM_USER_STATUS_NONE
}
