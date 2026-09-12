// 难度及配色（洛谷 8 级基础上自定义：「普及/提高-」并入「普及」，新增「提高」）
export const DIFFICULTY_LIST = [
  '暂无评定',
  '入门',
  '普及-',
  '普及',
  '普及+/提高',
  '提高',
  '提高+/省选-',
  '省选/NOI-',
  'NOI/NOI+/CTSC',
] as const

export const DIFFICULTY_COLORS: Record<string, string> = {
  暂无评定: '#bfbfbf',
  入门: '#fe4c61',
  '普及-': '#f39c11',
  普及: '#ffc116',
  '普及+/提高': '#52c41a',
  提高: '#13c2c2',
  '提高+/省选-': '#3498db',
  '省选/NOI-': '#9d3dcf',
  'NOI/NOI+/CTSC': '#0e1d69',
}

export function difficultyColor(d: string): string {
  return DIFFICULTY_COLORS[d] ?? DIFFICULTY_COLORS['暂无评定']
}
