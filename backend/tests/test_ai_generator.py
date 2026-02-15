"""
Tests for AIGenerator to verify it correctly calls CourseSearchTool
Tests tool calling behavior and response generation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from ai_generator import AIGenerator


# Create mock classes for anthropic types
class MockTextBlock:
    def __init__(self, type, text):
        self.type = type
        self.text = text


class MockToolUseBlock:
    def __init__(self, id, name, input, type):
        self.id = id
        self.name = name
        self.input = input
        self.type = type


class TestAIGeneratorToolCalling:
    """Test suite for AIGenerator's tool calling behavior"""

    def setup_method(self):
        """Setup test fixtures"""
        self.generator = AIGenerator(
            api_key="test_key",
            model="claude-sonnet-4-20250514"
        )

    def test_generate_response_without_tools(self):
        """Test response generation without tools"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MockTextBlock(type="text", text="Direct answer")]

        with patch.object(self.generator.client.messages, 'create', return_value=mock_response):
            result = self.generator.generate_response(
                query="What is Python?",
                tools=None,
                tool_manager=None
            )

        assert result == "Direct answer"

    def test_generate_response_with_tools_no_tool_use(self):
        """Test response with tools available but Claude doesn't use them"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MockTextBlock(type="text", text="General knowledge answer")]

        tool_definitions = [
            {
                "name": "search_course_content",
                "description": "Search course materials"
            }
        ]

        with patch.object(self.generator.client.messages, 'create', return_value=mock_response):
            result = self.generator.generate_response(
                query="What is the capital of France?",
                tools=tool_definitions,
                tool_manager=None
            )

        assert result == "General knowledge answer"

    def test_generate_response_with_tool_use(self):
        """Test response when Claude uses a tool"""
        # Mock initial response with tool use
        mock_tool_use = MockToolUseBlock(
            id="toolu_01",
            name="search_course_content",
            input={"query": "Python variables", "course_name": "Python"},
            type="tool_use"
        )

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_use]

        # Mock final response after tool execution
        mock_final_response = Mock()
        mock_final_response.content = [MockTextBlock(type="text", text="Based on the search...")]

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = (
            "[Python Course - Lesson 1]\nVariables are used to store data..."
        )

        with patch.object(self.generator.client.messages, 'create') as mock_create:
            mock_create.side_effect = [mock_initial_response, mock_final_response]

            result = self.generator.generate_response(
                query="Tell me about variables in Python",
                tools=[{
                    "name": "search_course_content",
                    "description": "Search course materials"
                }],
                tool_manager=mock_tool_manager
            )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once()
        call_args = mock_tool_manager.execute_tool.call_args
        assert call_args[0][0] == "search_course_content"
        assert "query" in call_args[1]

        # Verify final response was returned
        assert "Based on the search" in result

    def test_generate_response_with_outline_tool(self):
        """Test response when Claude uses the outline tool"""
        mock_tool_use = MockToolUseBlock(
            id="toolu_02",
            name="get_course_outline",
            input={"course_title": "Python"},
            type="tool_use"
        )

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_use]

        mock_final_response = Mock()
        mock_final_response.content = [MockTextBlock(type="text", text="Here is the course outline...")]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = (
            "Course: Python\nLink: http://example.com\nLessons (5 total):\n  Lesson 1: Intro..."
        )

        with patch.object(self.generator.client.messages, 'create') as mock_create:
            mock_create.side_effect = [mock_initial_response, mock_final_response]

            result = self.generator.generate_response(
                query="Show me the outline of the Python course",
                tools=[{
                    "name": "get_course_outline",
                    "description": "Get course outline"
                }],
                tool_manager=mock_tool_manager
            )

        # Verify outline tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "get_course_outline",
            course_title="Python"
        )

        assert "outline" in result.lower()

    def test_generate_response_with_conversation_history(self):
        """Test response generation includes conversation history"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MockTextBlock(type="text", text="Follow-up answer")]

        with patch.object(self.generator.client.messages, 'create', return_value=mock_response) as mock_create:
            result = self.generator.generate_response(
                query="What about lists?",
                conversation_history="User: What is Python?\nAI: Python is a language",
                tools=None,
                tool_manager=None
            )

        # Verify system prompt includes history
        call_kwargs = mock_create.call_args[1]
        assert "Previous conversation" in call_kwargs["system"]
        assert "What is Python?" in call_kwargs["system"]

        assert result == "Follow-up answer"

    def test_generate_response_tool_execution_error(self):
        """Test tool execution errors are handled gracefully"""
        mock_tool_use = MockToolUseBlock(
            id="toolu_03",
            name="search_course_content",
            input={"query": "test"},
            type="tool_use"
        )

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_use]

        # Claude should respond even with tool error
        mock_final_response = Mock()
        mock_final_response.content = [MockTextBlock(type="text", text="I couldn't find that information.")]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Error: No course found"

        with patch.object(self.generator.client.messages, 'create') as mock_create:
            mock_create.side_effect = [mock_initial_response, mock_final_response]

            result = self.generator.generate_response(
                query="Find something",
                tools=[{"name": "search_course_content", "description": "Search"}],
                tool_manager=mock_tool_manager
            )

        # Verify tool result was passed to Claude
        assert "I couldn't find that information" in result

    def test_generate_response_zero_temperature(self):
        """Test temperature is set to 0 for consistent responses"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MockTextBlock(type="text", text="Answer")]

        with patch.object(self.generator.client.messages, 'create', return_value=mock_response) as mock_create:
            self.generator.generate_response(query="Test")

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["temperature"] == 0

    def test_generate_response_max_tokens(self):
        """Test max_tokens is set correctly"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MockTextBlock(type="text", text="Answer")]

        with patch.object(self.generator.client.messages, 'create', return_value=mock_response) as mock_create:
            self.generator.generate_response(query="Test")

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["max_tokens"] == 800

    def test_system_prompt_includes_tool_guidance(self):
        """Test system prompt includes tool usage guidance"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MockTextBlock(type="text", text="Answer")]

        tool_definitions = [
            {"name": "search_course_content", "description": "Search"},
            {"name": "get_course_outline", "description": "Get outline"}
        ]

        with patch.object(self.generator.client.messages, 'create', return_value=mock_response) as mock_create:
            self.generator.generate_response(
                query="Test",
                tools=tool_definitions,
                tool_manager=None
            )

        call_kwargs = mock_create.call_args[1]
        system_prompt = call_kwargs["system"]

        # Verify tool guidance is present
        assert "Available Tools:" in system_prompt
        assert "search_course_content" in system_prompt
        assert "get_course_outline" in system_prompt


class TestAIGeneratorIntegration:
    """Integration tests for AIGenerator with real tool scenarios"""

    def setup_method(self):
        """Setup test fixtures"""
        self.generator = AIGenerator(
            api_key="test_key",
            model="claude-sonnet-4-20250514"
        )

    def test_content_query_triggers_search_tool(self):
        """Test that content-related queries trigger the search tool"""
        # This is a critical test - if the system prompt doesn't properly guide Claude,
        # it might not use the tool for content queries

        mock_tool_use = MockToolUseBlock(
            id="toolu_01",
            name="search_course_content",
            input={"query": "functions and methods"},
            type="tool_use"
        )

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_use]

        mock_final_response = Mock()
        mock_final_response.content = [MockTextBlock(type="text", text="Functions are...")]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "[Course - Lesson 5]\nFunctions are reusable blocks..."

        with patch.object(self.generator.client.messages, 'create') as mock_create:
            mock_create.side_effect = [mock_initial_response, mock_final_response]

            result = self.generator.generate_response(
                query="Explain functions and methods in the course",
                tools=[{
                    "name": "search_course_content",
                    "description": "Search course materials with semantic course name matching"
                }],
                tool_manager=mock_tool_manager
            )

        # Critical assertion: Verify the tool was called
        assert mock_tool_manager.execute_tool.called, "Tool should have been called for content query"

    def test_outline_query_triggers_outline_tool(self):
        """Test that outline-related queries trigger the outline tool"""
        mock_tool_use = MockToolUseBlock(
            id="toolu_02",
            name="get_course_outline",
            input={"course_title": "Python"},
            type="tool_use"
        )

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_use]

        mock_final_response = Mock()
        mock_final_response.content = [MockTextBlock(type="text", text="Course outline: ...")]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Course: Python\n\nLessons (5 total):"

        with patch.object(self.generator.client.messages, 'create') as mock_create:
            mock_create.side_effect = [mock_initial_response, mock_final_response]

            result = self.generator.generate_response(
                query="What lessons are in the Python course?",
                tools=[{
                    "name": "get_course_outline",
                    "description": "Get course outline"
                }],
                tool_manager=mock_tool_manager
            )

        # Critical assertion: Verify the outline tool was called
        mock_tool_manager.execute_tool.assert_called_once_with(
            "get_course_outline",
            course_title="Python"
        )


class TestSequentialToolCalling:
    """Test suite for sequential tool calling (2 rounds maximum)"""

    def setup_method(self):
        """Setup test fixtures"""
        self.generator = AIGenerator(
            api_key="test_key",
            model="claude-sonnet-4-20250514"
        )

    def test_two_round_sequential_tool_calls(self):
        """Test successful 2-round sequential tool calling"""
        # Round 1: Claude calls search_course_content
        mock_tool_use_1 = MockToolUseBlock(
            id="toolu_01",
            name="search_course_content",
            input={"query": "Python variables"},
            type="tool_use"
        )

        mock_response_1 = Mock()
        mock_response_1.stop_reason = "tool_use"
        mock_response_1.content = [mock_tool_use_1]

        # Round 2: Claude calls get_course_outline (based on round 1 results)
        mock_tool_use_2 = MockToolUseBlock(
            id="toolu_02",
            name="get_course_outline",
            input={"course_title": "Python"},
            type="tool_use"
        )

        mock_response_2 = Mock()
        mock_response_2.stop_reason = "tool_use"
        mock_response_2.content = [mock_tool_use_2]

        # Round 3: Final answer
        mock_final_response = Mock()
        mock_final_response.content = [MockTextBlock(type="text", text="Here's the comparison...")]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "[Python Course]\nVariables are...",
            "Course: Python\nLessons (10 total):..."
        ]

        with patch.object(self.generator.client.messages, 'create') as mock_create:
            mock_create.side_effect = [mock_response_1, mock_response_2, mock_final_response]

            result = self.generator.generate_response(
                query="Compare variables in Python course with its outline",
                tools=[{
                    "name": "search_course_content",
                    "description": "Search course materials"
                }],
                tool_manager=mock_tool_manager
            )

        # Verify 3 API calls (round 1, round 2, final)
        assert mock_create.call_count == 3

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify final response returned
        assert "comparison" in result.lower()

    def test_max_rounds_enforcement(self):
        """Test that max 2 rounds is enforced"""
        # Create scenario where Claude wants 3 rounds
        mock_tool_use_1 = MockToolUseBlock(id="toolu_01", name="search", input={}, type="tool_use")
        mock_tool_use_2 = MockToolUseBlock(id="toolu_02", name="search", input={}, type="tool_use")
        mock_tool_use_3 = MockToolUseBlock(id="toolu_03", name="search", input={}, type="tool_use")

        mock_response_1 = Mock(stop_reason="tool_use", content=[mock_tool_use_1])
        mock_response_2 = Mock(stop_reason="tool_use", content=[mock_tool_use_2])
        mock_response_3 = Mock(stop_reason="tool_use", content=[mock_tool_use_3])

        mock_final_response = Mock()
        mock_final_response.content = [MockTextBlock(type="text", text="Final answer")]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        with patch.object(self.generator.client.messages, 'create') as mock_create:
            # Should only make 4 calls: 2 tool rounds + 1 initial + 1 final
            mock_create.side_effect = [mock_response_1, mock_response_2, mock_response_3, mock_final_response]

            result = self.generator.generate_response(
                query="Test",
                tools=[{"name": "search", "description": "Search"}],
                tool_manager=mock_tool_manager
            )

        # Verify max 2 rounds enforced (4 calls: initial + round1 + round2 + final)
        assert mock_create.call_count == 4

    def test_early_termination_no_tool_use(self):
        """Test early termination when Claude doesn't use tools in second round"""
        # Round 1: Tool use
        mock_tool_use = MockToolUseBlock(
            id="toolu_01",
            name="search",
            input={},
            type="tool_use"
        )

        mock_response_1 = Mock()
        mock_response_1.stop_reason = "tool_use"
        mock_response_1.content = [mock_tool_use]

        # Round 2: No tool use (direct answer)
        mock_response_2 = Mock()
        mock_response_2.stop_reason = "end_turn"
        mock_response_2.content = [MockTextBlock(type="text", text="Answer based on search")]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search results"

        with patch.object(self.generator.client.messages, 'create') as mock_create:
            mock_create.side_effect = [mock_response_1, mock_response_2]

            result = self.generator.generate_response(
                query="Test",
                tools=[{"name": "search", "description": "Search"}],
                tool_manager=mock_tool_manager
            )

        # Verify only 2 API calls (round 1 + early termination)
        assert mock_create.call_count == 2
        assert "Answer based on search" in result

    def test_message_history_preserved_across_rounds(self):
        """Test that message history accumulates correctly across 2 rounds"""
        mock_tool_use = MockToolUseBlock(
            id="toolu_01",
            name="search",
            input={},
            type="tool_use"
        )

        mock_response_1 = Mock(stop_reason="tool_use", content=[mock_tool_use])
        mock_response_2 = Mock(stop_reason="end_turn", content=[MockTextBlock(type="text", text="Answer")])

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        with patch.object(self.generator.client.messages, 'create') as mock_create:
            mock_create.side_effect = [mock_response_1, mock_response_2]

            self.generator.generate_response(
                query="Test query",
                tools=[{"name": "search", "description": "Search"}],
                tool_manager=mock_tool_manager
            )

        # Verify message history structure
        # Call 1: Initial user query
        call_1_kwargs = mock_create.call_args_list[0][1]
        assert call_1_kwargs["messages"] == [{"role": "user", "content": "Test query"}]

        # Call 2: User query + assistant (tool_use) + user (tool_results)
        call_2_kwargs = mock_create.call_args_list[1][1]
        messages = call_2_kwargs["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_tool_execution_error_stops_loop(self):
        """Test that tool execution errors are handled and stop the loop"""
        mock_tool_use = MockToolUseBlock(
            id="toolu_01",
            name="search",
            input={},
            type="tool_use"
        )

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_use]

        mock_final_response = Mock()
        mock_final_response.content = [MockTextBlock(type="text", text="I encountered an error")]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool failed")

        with patch.object(self.generator.client.messages, 'create') as mock_create:
            mock_create.side_effect = [mock_initial_response, mock_final_response]

            result = self.generator.generate_response(
                query="Test",
                tools=[{"name": "search", "description": "Search"}],
                tool_manager=mock_tool_manager
            )

        # Should make 2 calls (initial tool use + final with error)
        assert mock_create.call_count == 2
        assert "I encountered an error" in result
