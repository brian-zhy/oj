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
