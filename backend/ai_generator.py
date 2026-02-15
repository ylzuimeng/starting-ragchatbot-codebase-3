import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
1. **search_course_content** - Search course materials with semantic course name matching and lesson filtering
   - Use for questions about specific course content or detailed educational materials
   - Supports filtering by course name and lesson number
   - **Multi-round searching**: You can make up to 2 sequential tool calls per query to gather comprehensive information

2. **get_course_outline** - Get course outline with title, link, and complete lesson list
   - Use for questions about course structure, syllabus, or lesson organization
   - Returns course title, course link, instructor, and all lessons (with numbers and titles)
   - Perfect for "what lessons are in this course?" or "show me the outline" type queries

Tool Usage Guidelines:
- Choose the most appropriate tool based on the user's question
- For outline-related queries, use get_course_outline to return complete course structure
- For content-related queries, use search_course_content to find specific information
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives
- **Sequential tool calling**: If the first tool call doesn't fully answer the question, you can make a second targeted call
- Examples:
  * Search one course, then search another course for comparison
  * Get course outline, then search for specific lesson content
  * Refine a search with additional filters based on initial results

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"
- **After tool use**: Build on previous tool results to provide comprehensive answers


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str, base_url: str = None):
        if base_url:
            self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        else:
            self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager) -> str:
        """
        Handle sequential tool execution with support for up to 2 rounds.

        Loop structure:
        - Round 0: Execute tools from initial response
        - Round 1: If Claude uses tools again, execute those tools
        - Final: Force answer without tools (or natural end if Claude provides text)

        Termination:
        - Natural: response.stop_reason != "tool_use"
        - Max rounds: 2 rounds completed
        - Error: Tool execution fails (pass error to Claude, stop looping)

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        MAX_TOOL_ROUNDS = 2

        # Initialize message history with user query
        messages = base_params["messages"].copy()

        # Add initial assistant response (contains tool_use blocks)
        messages.append({"role": "assistant", "content": initial_response.content})

        # Prepare for looping: get current response
        current_response = initial_response

        # Loop through sequential tool calling rounds
        for round_num in range(MAX_TOOL_ROUNDS):
            # Execute all tool calls from current response
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(
                            content_block.name,
                            **content_block.input
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": result
                        })
                    except Exception as e:
                        # Tool execution failed - pass error to Claude and stop
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Error: {str(e)}"
                        })
                        # Add error results and make final API call
                        messages.append({"role": "user", "content": tool_results})

                        final_params = {
                            **self.base_params,
                            "messages": messages,
                            "system": base_params["system"]
                        }
                        final_response = self.client.messages.create(**final_params)
                        return final_response.content[0].text

            # Add tool results as user message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            else:
                break  # No tool results, shouldn't happen but safe exit

            # Make next API call WITH tools (keep them available)
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                "tools": base_params.get("tools"),  # Keep tools available
                "tool_choice": {"type": "auto"}
            }

            try:
                current_response = self.client.messages.create(**next_params)
            except Exception as e:
                # API call failed - return graceful error
                return f"I encountered an error processing your request: {str(e)}"

            # Check if Claude wants to make another tool call
            has_tool_use = any(
                content.type == "tool_use"
                for content in current_response.content
            )

            if not has_tool_use:
                # Claude provided final answer - return it
                return current_response.content[0].text

            # Claude wants to call tools again - add assistant response and continue loop
            messages.append({"role": "assistant", "content": current_response.content})

        # Max rounds reached - force final answer without tools
        messages.append({"role": "assistant", "content": current_response.content})

        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
            # Note: No "tools" parameter - forces Claude to provide final answer
        }

        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text