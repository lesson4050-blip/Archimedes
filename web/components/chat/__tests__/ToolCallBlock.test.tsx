// @vitest-environment jsdom
import { describe, test, expect, afterEach } from "vitest"
import { render, screen, fireEvent, cleanup } from "@testing-library/react"
import React from "react"
import ToolCallBlock from "../ToolCallBlock"

describe("ToolCallBlock Component", () => {
  afterEach(() => {
    cleanup()
  })

  test("renders tool_call with correct tool name", () => {
    render(<ToolCallBlock type="tool_call" tool="web_search" payload={{ query: "react hooks" }} />)
    
    // Check tool name is rendered
    expect(screen.getByText(/\[web_search\]/i)).toBeDefined()
    expect(screen.getByRole("button")).toBeDefined()
    
    // The payload shouldn't be visible since it's collapsed by default
    expect(screen.queryByText(/react hooks/i)).toBeNull()
  })

  test("renders tool_result with success indicator", () => {
    const payload = { success: true, output: "Search results output here" }
    render(<ToolCallBlock type="tool_result" tool="web_search" payload={payload} />)
    
    expect(screen.getByText(/\[web_search\]/i)).toBeDefined()
  })

  test("expands and collapses on click", () => {
    const output = "This is a detailed secret output which is very long and is truncated in the preview."
    render(<ToolCallBlock type="tool_result" tool="web_search" payload={{ success: true, output }} />)
    
    // Not visible in its full untruncated form initially
    expect(screen.queryByText(output)).toBeNull()
    
    // Click header button to expand
    const button = screen.getByRole("button")
    fireEvent.click(button)
    
    // Detailed output should now be visible
    expect(screen.getByText(output)).toBeDefined()
    
    // Click again to collapse
    fireEvent.click(button)
    expect(screen.queryByText(output)).toBeNull()
  })
})
