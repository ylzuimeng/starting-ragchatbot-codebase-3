"""
Tests for CourseSearchTool and CourseOutlineTool
Tests the execute methods and error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from vector_store import VectorStore, SearchResults
from search_tools import CourseSearchTool, CourseOutlineTool


class TestCourseSearchTool:
    """Test suite for CourseSearchTool.execute() method"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_store = Mock(spec=VectorStore)
        self.tool = CourseSearchTool(self.mock_store)

    def test_execute_with_results(self):
        """Test execute returns formatted results when search succeeds"""
        # Setup mock to return valid search results
        mock_results = SearchResults(
            documents=["Chunk 1 content about Python", "Chunk 2 content about Java"],
            metadata=[
                {"course_title": "Python Course", "lesson_number": 1},
                {"course_title": "Java Course", "lesson_number": 2}
            ],
            distances=[0.1, 0.2],
            error=None
        )
        self.mock_store.search.return_value = mock_results
        self.mock_store.get_lesson_link.return_value = "http://example.com/lesson/1"
        self.mock_store.get_course_link.return_value = "http://example.com/course"

        # Execute the tool
        result = self.tool.execute(query="programming languages")

        # Verify search was called correctly
        self.mock_store.search.assert_called_once_with(
            query="programming languages",
            course_name=None,
            lesson_number=None
        )

        # Verify result format
        assert "[Python Course - Lesson 1]" in result
        assert "Chunk 1 content about Python" in result
        assert "[Java Course - Lesson 2]" in result
        assert "Chunk 2 content about Java" in result

        # Verify sources are tracked
        assert len(self.tool.last_sources) == 2
        assert self.tool.last_sources[0]["text"] == "Python Course - Lesson 1"
        assert self.tool.last_sources[0]["link"] == "http://example.com/lesson/1"

    def test_execute_with_course_filter(self):
        """Test execute with course name filter"""
        mock_results = SearchResults(
            documents=["Course content"],
            metadata=[{"course_title": "Python Course", "lesson_number": 1}],
            distances=[0.1],
            error=None
        )
        self.mock_store.search.return_value = mock_results
        self.mock_store.get_lesson_link.return_value = "http://example.com/lesson/1"
        self.mock_store.get_course_link.return_value = "http://example.com/course"

        result = self.tool.execute(
            query="data types",
            course_name="Python"
        )

        self.mock_store.search.assert_called_once_with(
            query="data types",
            course_name="Python",
            lesson_number=None
        )
        assert "Course content" in result

    def test_execute_with_lesson_filter(self):
        """Test execute with lesson number filter"""
        mock_results = SearchResults(
            documents=["Lesson content"],
            metadata=[{"course_title": "Python Course", "lesson_number": 3}],
            distances=[0.1],
            error=None
        )
        self.mock_store.search.return_value = mock_results
        self.mock_store.get_lesson_link.return_value = None
        self.mock_store.get_course_link.return_value = "http://example.com/course"

        result = self.tool.execute(
            query="functions",
            lesson_number=3
        )

        self.mock_store.search.assert_called_once_with(
            query="functions",
            course_name=None,
            lesson_number=3
        )
        assert "Lesson content" in result

    def test_execute_with_no_results(self):
        """Test execute handles empty results gracefully"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_store.search.return_value = mock_results

        result = self.tool.execute(query="nonexistent topic")

        assert result == "No relevant content found."

    def test_execute_with_no_results_filtered(self):
        """Test execute handles empty results with filters"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_store.search.return_value = mock_results

        result = self.tool.execute(
            query="something",
            course_name="Python",
            lesson_number=5
        )

        assert "in course 'Python'" in result
        assert "in lesson 5" in result

    def test_execute_with_search_error(self):
        """Test execute propagates search errors"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Connection failed"
        )
        self.mock_store.search.return_value = mock_results

        result = self.tool.execute(query="test")

        assert result == "Connection failed"

    def test_execute_with_zero_max_results(self):
        """Test execute behavior when vector store returns 0 results (config issue)"""
        # This simulates the MAX_RESULTS=0 bug
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_store.search.return_value = mock_results

        result = self.tool.execute(query="test query")

        # Should return empty results message, not an error
        assert result == "No relevant content found."

    def test_get_tool_definition(self):
        """Test tool definition structure"""
        definition = self.tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]
        assert "query" in definition["input_schema"]["required"]


class TestCourseOutlineTool:
    """Test suite for CourseOutlineTool.execute() method"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_store = Mock(spec=VectorStore)
        self.tool = CourseOutlineTool(self.mock_store)

    def test_execute_successful_outline(self):
        """Test execute returns formatted outline"""
        import json

        # Mock course name resolution
        self.mock_store._resolve_course_name.return_value = "Complete Python Course"

        # Mock course metadata retrieval
        lessons_metadata = [
            {"lesson_number": 0, "lesson_title": "Introduction", "lesson_link": "http://example.com/0"},
            {"lesson_number": 1, "lesson_title": "Variables", "lesson_link": "http://example.com/1"},
            {"lesson_number": 2, "lesson_title": "Functions", "lesson_link": "http://example.com/2"}
        ]

        # Setup mock course_catalog
        mock_catalog = Mock()
        mock_catalog.get.return_value = {
            'metadatas': [{
                'title': 'Complete Python Course',
                'course_link': 'http://example.com/course',
                'instructor': 'John Doe',
                'lessons_json': json.dumps(lessons_metadata)
            }]
        }
        self.mock_store.course_catalog = mock_catalog

        # Execute
        result = self.tool.execute(course_title="Python")

        # Verify
        assert "Course: Complete Python Course" in result
        assert "Link: http://example.com/course" in result
        assert "Instructor: John Doe" in result
        assert "Lessons (3 total):" in result
        assert "Lesson 0: Introduction" in result
        assert "Lesson 1: Variables" in result
        assert "Lesson 2: Functions" in result

    def test_execute_course_not_found(self):
        """Test execute when course doesn't exist"""
        self.mock_store._resolve_course_name.return_value = None

        result = self.tool.execute(course_title="Nonexistent Course")

        assert "No course found matching 'Nonexistent Course'" in result

    def test_execute_metadata_error(self):
        """Test execute when metadata retrieval fails"""
        self.mock_store._resolve_course_name.return_value = "Python Course"

        mock_catalog = Mock()
        mock_catalog.get.return_value = None
        self.mock_store.course_catalog = mock_catalog

        result = self.tool.execute(course_title="Python")

        assert "Error retrieving course data" in result

    def test_execute_no_lessons(self):
        """Test execute when course has no lessons"""
        import json

        self.mock_store._resolve_course_name.return_value = "Empty Course"

        mock_catalog = Mock()
        mock_catalog.get.return_value = {
            'metadatas': [{
                'title': 'Empty Course',
                'course_link': 'http://example.com/empty',
                'instructor': 'Jane Doe',
                'lessons_json': None
            }]
        }
        self.mock_store.course_catalog = mock_catalog

        result = self.tool.execute(course_title="Empty")

        assert "No lesson information available" in result

    def test_get_tool_definition(self):
        """Test tool definition structure"""
        definition = self.tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"
        assert "course_title" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["course_title"]


class TestToolManager:
    """Test suite for ToolManager"""

    def setup_method(self):
        """Setup test fixtures"""
        from search_tools import ToolManager
        self.manager = ToolManager()
        self.mock_tool = Mock()
        self.mock_tool.get_tool_definition.return_value = {
            "name": "test_tool",
            "description": "Test tool"
        }

    def test_register_tool(self):
        """Test tool registration"""
        self.manager.register_tool(self.mock_tool)

        assert "test_tool" in self.manager.tools

    def test_register_tool_no_name(self):
        """Test registration fails for tool without name"""
        self.mock_tool.get_tool_definition.return_value = {"description": "No name"}

        with pytest.raises(ValueError, match="Tool must have a 'name'"):
            self.manager.register_tool(self.mock_tool)

    def test_execute_tool(self):
        """Test tool execution"""
        self.mock_tool.execute.return_value = "Tool executed"
        self.manager.register_tool(self.mock_tool)

        result = self.manager.execute_tool("test_tool", param1="value")

        assert result == "Tool executed"
        self.mock_tool.execute.assert_called_once_with(param1="value")

    def test_execute_tool_not_found(self):
        """Test execution of non-existent tool"""
        result = self.manager.execute_tool("nonexistent")

        assert "not found" in result

    def test_get_last_sources(self):
        """Test retrieving last sources"""
        self.mock_tool.execute.return_value = "Result"
        self.mock_tool.last_sources = [{"text": "Source 1", "link": "http://example.com"}]
        self.manager.register_tool(self.mock_tool)

        sources = self.manager.get_last_sources()

        assert len(sources) == 1
        assert sources[0]["text"] == "Source 1"

    def test_reset_sources(self):
        """Test resetting sources"""
        self.mock_tool.execute.return_value = "Result"
        self.mock_tool.last_sources = [{"text": "Source 1", "link": "http://example.com"}]
        self.manager.register_tool(self.mock_tool)

        self.manager.reset_sources()

        assert self.mock_tool.last_sources == []

    def test_get_tool_definitions(self):
        """Test getting all tool definitions"""
        self.manager.register_tool(self.mock_tool)
        definitions = self.manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "test_tool"
