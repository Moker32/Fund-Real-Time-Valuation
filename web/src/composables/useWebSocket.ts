import { ref, onUnmounted } from 'vue'

export type MessageType =
  | 'fund_update'
  | 'commodity_update'
  | 'index_update'
  | 'sector_update'
  | 'data_update'
  | 'subscribed'
  | 'subscriptions'
  | 'pong'
  | 'error'

export interface WSMessage {
  type: MessageType
  data: unknown
  timestamp: string
}

export type SubscriptionType = 'funds' | 'commodities' | 'indices' | 'sectors' | 'all'

export interface UseWebSocketOptions {
  url?: string
  autoReconnect?: boolean
  reconnectInterval?: number
  onMessage?: (message: WSMessage) => void
  onConnected?: () => void
  onDisconnected?: () => void
  onError?: (error: Event) => void
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    url = `ws://${window.location.host}/ws/realtime`,
    autoReconnect = true,
    reconnectInterval = 3000,
    onMessage,
    onConnected,
    onDisconnected,
    onError,
  } = options

  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const subscriptions = ref<Set<SubscriptionType>>(new Set())
  const lastMessage = ref<WSMessage | null>(null)
  const error = ref<Event | null>(null)

  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null

  // 待发送的消息队列（连接建立前缓存）
  const pendingMessages: { action: string; data?: unknown }[] = []

  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      isConnected.value = true
      error.value = null

      // 发送待处理的消息
      while (pendingMessages.length > 0) {
        const msg = pendingMessages.shift()
        if (msg) {
          send(msg.action, msg.data)
        }
      }

      // 重连后重新订阅之前的频道
      if (subscriptions.value.size > 0) {
        send('subscribe', Array.from(subscriptions.value))
      }

      onConnected?.()
      startHeartbeat()
    }

    ws.value.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)
        lastMessage.value = message
        onMessage?.(message)
      } catch {
        // 忽略解析错误
      }
    }

    ws.value.onerror = (e) => {
      error.value = e
      onError?.(e)
    }

    ws.value.onclose = () => {
      isConnected.value = false
      stopHeartbeat()
      onDisconnected?.()

      if (autoReconnect) {
        reconnectTimer = setTimeout(() => {
          connect()
        }, reconnectInterval)
      }
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    stopHeartbeat()

    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    isConnected.value = false
    subscriptions.value.clear()
  }

  function send(action: string, data?: unknown) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ action, data }))
    } else if (ws.value?.readyState === WebSocket.CONNECTING) {
      // 连接建立中，缓存消息
      pendingMessages.push({ action, data })
    } else {
      console.warn('[WS] 无法发送消息，连接未建立:', action)
    }
  }

  function subscribe(types: SubscriptionType | SubscriptionType[]) {
    const typeList = Array.isArray(types) ? types : [types]
    send('subscribe', typeList)
    typeList.forEach(t => subscriptions.value.add(t))
  }

  function unsubscribe(types: SubscriptionType | SubscriptionType[]) {
    const typeList = Array.isArray(types) ? types : [types]
    send('unsubscribe', typeList)
    typeList.forEach(t => subscriptions.value.delete(t))
  }

  function ping() {
    send('ping')
  }

  function startHeartbeat() {
    stopHeartbeat()
    heartbeatTimer = setInterval(() => {
      if (isConnected.value) {
        ping()
      }
    }, 30000)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    ws,
    isConnected,
    subscriptions,
    lastMessage,
    error,
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    ping,
  }
}
