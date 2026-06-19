import { ref, watch, onBeforeUnmount } from 'vue'

/**
 * useMenuAim - Vue 3 Composable for nested dropdown/context menus.
 * Implements Amazon-style directional mouse-aiming (Prediction Cone / Safe Triangle)
 * to prevent submenus from closing prematurely when moving the cursor diagonally.
 *
 * @param {Object} options
 * @param {string} [options.submenuDirection='right'] - Direction of the submenu relative to parent ('right' | 'left')
 * @param {number} [options.delay=300] - Delay in milliseconds before switching when inside the safe triangle
 * @returns {Object} Helper refs and handlers to plug into the menu component
 */
export function useMenuAim(options = {}) {
  const {
    submenuDirection = 'right',
    delay = 300,
    isVisible = null
  } = options

  // Ref to be bound to the currently open submenu element (e.g. ref="submenuRef")
  const submenuRef = ref(null)

  // Track recent mouse coordinates to construct the direction vector
  const mouseLocs = ref([])

  // Track the currently active menu item ID
  const activeItemId = ref(null)

  // Track if mouse is over the submenu itself
  const isMouseInSubmenu = ref(false)

  // Debug settings for visual rendering
  const debugConeActive = ref(false)
  const trianglePoints = ref(null)
  const triggerAnchor = ref(null)

  let timeoutId = null
  let pendingActivation = null
  let pendingCloseCallback = null
  let closeTimeoutId = null

  /**
   * Helper mathematical function: Check if point P is inside triangle ABC
   * using the sign of cross-products (edge side functions).
   */
  const isPointInTriangle = (p, a, b, c) => {
    const d1 = (p.x - b.x) * (a.y - b.y) - (a.x - b.x) * (p.y - b.y)
    const d2 = (p.x - c.x) * (b.y - c.y) - (b.x - c.x) * (p.y - c.y)
    const d3 = (p.x - a.x) * (c.y - a.y) - (c.x - a.x) * (p.y - a.y)

    const has_neg = (d1 < 0) || (d2 < 0) || (d3 < 0)
    const has_pos = (d1 > 0) || (d2 > 0) || (d3 > 0)

    return !(has_neg && has_pos)
  }

  /**
   * Check if current coordinate (x, y) falls within the Safe Triangle
   * formed by the previous cursor position and the open submenu's vertical edge.
   */
  const checkMouseInTriangle = (x, y) => {
    if (!submenuRef.value) return false
    
    const el = submenuRef.value.el || submenuRef.value.$el || submenuRef.value
    if (!el || typeof el.getBoundingClientRect !== 'function') return false

    const rect = el.getBoundingClientRect()
    if (rect.width === 0 || rect.height === 0) return false

    // Ensure mouse is moving in the direction of the submenu (from trigger towards submenu)
    const prevLoc = mouseLocs.value[0]
    if (prevLoc) {
      if (submenuDirection === 'left' && x >= prevLoc.x) {
        return false // Moving right or vertically: not aiming at submenu
      }
      if (submenuDirection === 'right' && x <= prevLoc.x) {
        return false // Moving left or vertically: not aiming at submenu
      }
    }

    // Vertex A: Static trigger anchor coordinate or cursor position at start of transition
    const a = triggerAnchor.value || mouseLocs.value[0] || { x, y }

    // Vertices B and C are the top and bottom corners of the submenu's active edge
    let b, c
    if (submenuDirection === 'right') {
      // Submenu is to the right: edge is the left edge of the submenu
      b = { x: rect.left, y: rect.top }
      c = { x: rect.left, y: rect.bottom }
    } else {
      // Submenu is to the left: edge is the right edge of the submenu
      b = { x: rect.right, y: rect.top }
      c = { x: rect.right, y: rect.bottom }
    }

    // Save points dynamically for debug rendering
    trianglePoints.value = { a, b, c }

    const p = { x, y }
    return isPointInTriangle(p, a, b, c)
  }

  /**
   * Immediately trigger any pending hover activation
   */
  const triggerPending = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    if (pendingActivation) {
      const { itemId, activate } = pendingActivation
      pendingActivation = null
      activeItemId.value = itemId
      activate()
    }
  }

  /**
   * Clear pending close timeout
   */
  const clearCloseTimeout = () => {
    if (closeTimeoutId) {
      clearTimeout(closeTimeoutId)
      closeTimeoutId = null
    }
    pendingCloseCallback = null
  }

  /**
   * Immediately trigger pending close callback
   */
  const triggerClose = () => {
    if (closeTimeoutId) {
      clearTimeout(closeTimeoutId)
      closeTimeoutId = null
    }
    if (pendingCloseCallback) {
      const cb = pendingCloseCallback
      pendingCloseCallback = null
      cb()
    }
  }

  /**
   * Request closing the submenu. Delays if cursor is aiming towards it or inside it.
   */
  const requestClose = (closeCallback) => {
    const currentLoc = mouseLocs.value[mouseLocs.value.length - 1]
    const x = currentLoc ? currentLoc.x : 0
    const y = currentLoc ? currentLoc.y : 0

    if (isMouseInSubmenu.value || checkMouseInTriangle(x, y)) {
      clearCloseTimeout()
      pendingCloseCallback = closeCallback
    } else {
      clearCloseTimeout()
      closeCallback()
    }
  }

  /**
   * Handle global mousemove event to dynamically track aim direction
   */
  const handleMouseMove = (e) => {
    mouseLocs.value.push({ x: e.clientX, y: e.clientY })
    if (mouseLocs.value.length > 5) {
      mouseLocs.value.shift()
    }

    const isInside = checkMouseInTriangle(e.clientX, e.clientY)

    // Clear triangle points if we are inside the submenu itself
    if (isMouseInSubmenu.value) {
      trianglePoints.value = null
    }

    // Case 1: Pending item switch
    if (pendingActivation) {
      if (!isInside) {
        triggerPending()
      } else {
        // Reset activation timeout because they are still moving inside the safe triangle
        clearTimeout(timeoutId)
        timeoutId = setTimeout(() => {
          triggerPending()
        }, delay)
      }
    }

    // Case 2: Pending menu close
    if (pendingCloseCallback) {
      if (!isInside && !isMouseInSubmenu.value) {
        triggerClose()
      }
    }
  }

  /**
   * Handler to be called on a menu item's `@mouseenter`.
   * Either activates it immediately, or delays activation if user is aiming at the submenu.
   *
   * @param {string|number} itemId - Unique identifier for the hovered item
   * @param {Function} activate - Callback function to open this item's submenu
   */
  const onItemHover = (itemId, activate, anchorCoords = null) => {
    if (anchorCoords) {
      triggerAnchor.value = anchorCoords
    }

    // If we're hovering the already active item, cancel any pending activation of other items
    if (activeItemId.value === itemId) {
      if (pendingActivation && pendingActivation.itemId === itemId) {
        if (timeoutId) {
          clearTimeout(timeoutId)
          timeoutId = null
        }
        pendingActivation = null
      }
      return
    }

    // Get last tracked mouse location
    const currentLoc = mouseLocs.value[mouseLocs.value.length - 1]
    const x = currentLoc ? currentLoc.x : 0
    const y = currentLoc ? currentLoc.y : 0

    // Check if mouse is in the safe triangle
    const isInsideTriangle = checkMouseInTriangle(x, y)

    if (isInsideTriangle) {
      // User is aiming towards the submenu: delay the switch
      if (timeoutId) clearTimeout(timeoutId)
      pendingActivation = { itemId, activate }
      
      timeoutId = setTimeout(() => {
        triggerPending()
      }, delay)
    } else {
      // User is moving elsewhere: switch immediately
      if (timeoutId) {
        clearTimeout(timeoutId)
        timeoutId = null
      }
      pendingActivation = null
      activeItemId.value = itemId
      activate()
    }
  }

  /**
   * Handler to be called when mouse leaves the parent menu container
   */
  const onMouseLeaveMenu = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    pendingActivation = null
  }

  /**
   * Clear all active state and timers (useful on menu close)
   */
  const reset = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    if (closeTimeoutId) {
      clearTimeout(closeTimeoutId)
      closeTimeoutId = null
    }
    pendingActivation = null
    pendingCloseCallback = null
    activeItemId.value = null
    mouseLocs.value = []
    isMouseInSubmenu.value = false
    trianglePoints.value = null
    triggerAnchor.value = null
  }

  const handleSubmenuMouseEnter = () => {
    isMouseInSubmenu.value = true
    clearCloseTimeout()
    trianglePoints.value = null
  }

  const handleSubmenuMouseLeave = () => {
    isMouseInSubmenu.value = false
    triggerClose()
  }

  // Dynamic global event listener management based on active submenu visibility
  if (isVisible !== null) {
    watch(isVisible, async (visibleVal) => {
      if (visibleVal) {
        window.addEventListener('mousemove', handleMouseMove)
        if (debugConeActive.value) {
          // Calculate initial points immediately
          await new Promise(resolve => setTimeout(resolve, 0))
          const currentLoc = mouseLocs.value[mouseLocs.value.length - 1]
          if (currentLoc) {
            checkMouseInTriangle(currentLoc.x, currentLoc.y)
          } else {
            // Default mock triangle if no mouse movement is recorded yet
            if (submenuRef.value) {
              const el = submenuRef.value.el || submenuRef.value.$el || submenuRef.value
              if (el && typeof el.getBoundingClientRect === 'function') {
                const rect = el.getBoundingClientRect()
                if (rect.width > 0 && rect.height > 0) {
                  if (submenuDirection === 'left') {
                    const b = { x: rect.right, y: rect.top }
                    const c = { x: rect.right, y: rect.bottom }
                    const a = { x: rect.right + 120, y: (rect.top + rect.bottom) / 2 }
                    trianglePoints.value = { a, b, c }
                    triggerAnchor.value = a
                  } else {
                    const b = { x: rect.left, y: rect.top }
                    const c = { x: rect.left, y: rect.bottom }
                    const a = { x: rect.left - 120, y: (rect.top + rect.bottom) / 2 }
                    trianglePoints.value = { a, b, c }
                    triggerAnchor.value = a
                  }
                }
              }
            }
          }
        }
      } else {
        window.removeEventListener('mousemove', handleMouseMove)
        reset()
      }
    })
  }

  // Recalculate triangle points immediately when active item changes (e.g. switching items)
  watch(activeItemId, async (newId) => {
    if (newId && debugConeActive.value) {
      await new Promise(resolve => setTimeout(resolve, 0))
      const currentLoc = mouseLocs.value[mouseLocs.value.length - 1]
      const x = currentLoc ? currentLoc.x : 0
      const y = currentLoc ? currentLoc.y : 0
      checkMouseInTriangle(x, y)
    }
  })

  onBeforeUnmount(() => {
    window.removeEventListener('mousemove', handleMouseMove)
    reset()
  })

  // Expose to window for console activation
  if (typeof window !== 'undefined') {
    window.enablePredictionConeDebug = (enabled = true) => {
      debugConeActive.value = enabled
      if (!enabled) {
        reset()
      } else {
        // Mock a triangle if none exists yet and the tooltip is open, so it is visible immediately
        if (submenuRef.value) {
          const el = submenuRef.value.el || submenuRef.value.$el || submenuRef.value
          if (el && typeof el.getBoundingClientRect === 'function') {
            const rect = el.getBoundingClientRect()
            if (rect.width > 0 && rect.height > 0) {
              if (submenuDirection === 'left') {
                const b = { x: rect.right, y: rect.top }
                const c = { x: rect.right, y: rect.bottom }
                const a = { x: rect.right + 120, y: (rect.top + rect.bottom) / 2 }
                trianglePoints.value = { a, b, c }
                triggerAnchor.value = a
              } else {
                const b = { x: rect.left, y: rect.top }
                const c = { x: rect.left, y: rect.bottom }
                const a = { x: rect.left - 120, y: (rect.top + rect.bottom) / 2 }
                trianglePoints.value = { a, b, c }
                triggerAnchor.value = a
              }
            }
          }
        }
      }
      console.log(`Prediction Cone Debug Mode: ${enabled ? 'ENABLED' : 'DISABLED'}`)
    }
  }

  return {
    submenuRef,
    activeItemId,
    onItemHover,
    onMouseLeaveMenu,
    requestClose,
    debugConeActive,
    trianglePoints,
    reset,
    handleSubmenuMouseEnter,
    handleSubmenuMouseLeave
  }
}
