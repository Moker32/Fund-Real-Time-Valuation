import { ref, onUnmounted } from 'vue'

export type MessageType = 
  | 'fund_update'
  | 'commodity_update'
  | 'index_update'
  | 'sector_update'
  | 'stock_update'
  | 'bond_update'
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

export type SubscriptionType = 'funds' | 'commodities' | 'indices' | 'sectors' | 'stocks' | 'bonds' | 'all'

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

  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      console.log('[WS] Connected')
      isConnected.value = true
      error.value = null
      onConnected?.()
      startHeartbeat()
    }

    ws.value.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)
        lastMessage.value = message
        onMessage?.(message)
      } catch (e) {
        console.error('[WS] Failed to parse message:', e)
      }
    }

    ws.value.onerror = (e) => {
      console.error('[WS] Error:', e)
      error.value = e
      onError?.(e)
    }

    ws.value.onclose = () => {
      console.log('[WS] Disconnected')
      isConnected.value = false
      stopHeartbeat()
      onDisconnected?.()

      if (autoReconnect) {
        reconnectTimer = setTimeout(() => {
          console.log('[WS] Reconnecting...')
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
