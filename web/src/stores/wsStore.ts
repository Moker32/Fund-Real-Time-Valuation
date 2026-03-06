import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useWebSocket, type SubscriptionType, type WSMessage } from '@/composables/useWebSocket'

export const useWSStore = defineStore('websocket', () => {
  const messageHandlers = ref<Map<string, ((data: unknown) => void)[]>>(new Map())

  const ws = useWebSocket({
    autoReconnect: true,
    reconnectInterval: 3000,
    onMessage: (message: WSMessage) => {
      // 当收到消息时，触发对应的处理器
      console.log('[WSStore] 收到消息:', message.type, message.data)
      const handlers = messageHandlers.value.get(message.type)
      if (handlers) {
        handlers.forEach(handler => {
          try {
            handler(message.data)
          } catch (e) {
            console.error('[WSStore] 处理器执行错误:', e)
          }
        })
      }
    },
    onConnected: () => {
      // 触发连接成功事件
      const handlers = messageHandlers.value.get('connected')
      if (handlers) {
        handlers.forEach(handler => {
          try {
            handler({ connected: true })
          } catch (e) {
            console.error('[WSStore] 连接处理器执行错误:', e)
          }
        })
      }
    },
    onDisconnected: () => {
      // 触发断开连接事件
      const handlers = messageHandlers.value.get('disconnected')
      if (handlers) {
        handlers.forEach(handler => {
          try {
            handler({ connected: false })
          } catch (e) {
            console.error('[WSStore] 断开连接处理器执行错误:', e)
          }
        })
      }
    },
  })

  const subscriptions = ref<Set<SubscriptionType>>(new Set())

  function on(type: string, handler: (data: unknown) => void) {
    if (!messageHandlers.value.has(type)) {
      messageHandlers.value.set(type, [])
    }
    messageHandlers.value.get(type)!.push(handler)
  }

  function off(type: string, handler: (data: unknown) => void) {
    const handlers = messageHandlers.value.get(type)
    if (handlers) {
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  function connect() {
    ws.connect()
  }

  function disconnect() {
    ws.disconnect()
  }

  function subscribe(types: SubscriptionType | SubscriptionType[]) {
    const typeList = Array.isArray(types) ? types : [types]
    ws.subscribe(typeList)
    typeList.forEach(t => subscriptions.value.add(t))
  }

  function unsubscribe(types: SubscriptionType | SubscriptionType[]) {
    const typeList = Array.isArray(types) ? types : [types]
    ws.unsubscribe(typeList)
    typeList.forEach(t => subscriptions.value.delete(t))
  }

  return {
    isConnected: computed(() => ws.isConnected.value),
    subscriptions: computed(() => ws.subscriptions.value),
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    on,
    off,
    lastMessage: computed(() => ws.lastMessage.value),
  }
})
