import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useWebSocket, type WSMessage, type SubscriptionType } from '@/composables/useWebSocket'

export const useWSStore = defineStore('websocket', () => {
  const ws = useWebSocket({
    autoReconnect: true,
    reconnectInterval: 3000,
  })

  const isConnected = ref(false)
  const subscriptions = ref<Set<SubscriptionType>>(new Set())
  const messageHandlers = ref<Map<string, ((data: unknown) => void)[]>>(new Map())

  function handleMessage(message: WSMessage) {
    const handlers = messageHandlers.value.get(message.type)
    if (handlers) {
      handlers.forEach(handler => handler(message.data))
    }
  }

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
