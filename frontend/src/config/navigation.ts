import type { NavGroup } from '../types/navigation'

export const NAV_GROUPS: NavGroup[] = [
  {
    title: 'CORE',
    items: [
      { id: 'overview', label: 'Overview', iconName: 'overview' },
      { id: 'investigations', label: 'Investigations', iconName: 'investigations' },
      { id: 'graph-explorer', label: 'Graph Explorer', iconName: 'graph' },
    ],
  },
  {
    title: 'EVIDENCE & INTELLIGENCE',
    items: [
      { id: 'evidence', label: 'Evidence', iconName: 'evidence' },
    ],
  },
  {
    title: 'OPERATIONS',
    items: [
      { id: 'attack-lab', label: 'Attack Lab', iconName: 'attack-lab' },
      { id: 'evaluation', label: 'Evaluation', iconName: 'evaluation' },
    ],
  },
]
