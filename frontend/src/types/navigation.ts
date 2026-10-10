export type NavItemId =
  | 'overview'
  | 'investigations'
  | 'graph-explorer'
  | 'case-review'
  | 'evidence'
  | 'attack-lab'
  | 'evaluation'

export interface NavItem {
  id: NavItemId
  label: string
  iconName: string
}

export interface NavGroup {
  title: string
  items: NavItem[]
}
