export interface CrawlerConfig {
  platform: string
  login_type: string
  crawler_type: string
  keywords: string
  specified_ids: string  // 详情模式下的帖子/视频ID
  creator_ids: string    // 创作者模式下的创作者ID
  start_page: number
  sort_type: string  // 搜索结果排序（仅小红书搜索模式生效）
  filter_start_date: string  // 发布时间筛选起始（YYYY-MM-DD，留空不限）
  filter_end_date: string    // 发布时间筛选结束（YYYY-MM-DD，留空不限）
  max_notes_count: number | null  // 抓取数量上限，null 表示使用配置默认值
  enable_comments: boolean
  enable_sub_comments: boolean
  enable_media: boolean  // 是否下载媒体（封面/视频/图文图片），支持 xhs/dy/ks/bili/wb
  save_option: string
  cookies: string
  headless: boolean
}

export interface CrawlerStatus {
  status: 'idle' | 'running' | 'stopping' | 'error'
  platform: string | null
  crawler_type: string | null
  started_at: string | null
  error_message: string | null
}

export interface LogEntry {
  id: number
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success' | 'debug'
  message: string
}

export interface DataFile {
  name: string
  path: string
  size: number
  modified_at: number
  record_count: number | null
  type: string
}

export interface Platform {
  value: string
  label: string
  icon: string
}

export interface ConfigOption {
  value: string
  label: string
}
