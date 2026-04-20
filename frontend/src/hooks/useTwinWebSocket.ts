import { useEffect, useRef } from 'react'
import { useTwinStore } from '../store/twinStore'
import type { TwinState } from '../types'

const WS_URL = `ws://${window.location.host}/ws`
const RECONNECT_MS = 2000

export function useTwinWebSocket() {
  const { setState, setConnected } = useTwinStore()
  const wsRef = useRef<WebSocket | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)

      ws.onmessage = (e) => {
        try {
          const data: TwinState = JSON.parse(e.data)
          setState(data)
        } catch {
          // ignore malformed frames
        }
      }

      ws.onclose = () => {
        setConnected(false)
        timerRef.current = setTimeout(connect, RECONNECT_MS)
      }

      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      timerRef.current && clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [setState, setConnected])
}
