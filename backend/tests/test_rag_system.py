"""
Tests for RAG System to evaluate end-to-end query handling
Tests the complete flow from query to response with sources
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from rag_system import RAGSystem
from config import Config


class TestRAGSystemQueryFlow:
    """Test suite for RAG system query handling"""

    def setup_method(self):
        """Setup test fixtures with mocked dependencies"""
        # Create a mock config
        self.config = Mock(spec=Config)
        self.config.CHROMA_PATH = "./test_chroma_db"
        self.config.CHUNK_SIZE = 800
        self.config.CHUNK_OVERLAP = 100
        self.config.MAX_RESULTS = 5  # Note: This should not be 0!
        self.config.MAX_HISTORY = 2
        self.config.ZHIPUAI_API_KEY = "test_key"

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.CourseSearchTool')
    @patch('rag_system.CourseOutlineTool')
    @patch('rag_system.ToolManager')
    def test_query_success_with_search_results(
        self, mock_tool_manager, mock_outline_tool, mock_search_tool,
        mock_doc_processor, mock_session_manager, mock_ai_generator,
        mock_vector_store_class
    ):
        """Test successful query flow with search results"""
        # Setup mocks
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        mock_ai = Mock()
        mock_ai_generator.return_value = mock_ai

        mock_session_mgr = Mock()
        mock_session_manager.return_value = mock_session_mgr
        mock_session_mgr.get_conversation_history.return_value = None  # No history

        mock_tool_mgr = Mock()
        mock_tool_manager.return_value = mock_tool_mgr

        # Mock tool manager methods
        mock_tool_mgr.get_tool_definitions.return_value = [
            {"name": "search_course_content", "description": "Search"}
        ]
        mock_tool_mgr.get_last_sources.return_value = [
            {"text": "Python Course - Lesson 1", "link": "http://example.com/lesson1"}
        ]
        mock_ai.generate_response.return_value = "Python is a programming language..."

        # Create RAG system
        rag = RAGSystem(self.config)

        # Execute query
        response, sources = rag.query("What is Python?")

        # Verify flow (get_conversation_history is called with session_id, None in this case)
        mock_session_mgr.get_conversation_history.assert_called_once_with(None)
        mock_ai.generate_response.assert_called_once()
        mock_tool_mgr.get_last_sources.assert_called_once()
        mock_tool_mgr.reset_sources.assert_called_once()

        # Verify response
        assert response == "Python is a programming language..."
        assert len(sources) == 1
        assert sources[0]["text"] == "Python Course - Lesson 1"

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.CourseSearchTool')
    @patch('rag_system.CourseOutlineTool')
    @patch('rag_system.ToolManager')
    def test_query_with_session_id(
        self, mock_tool_manager, mock_outline_tool, mock_search_tool,
        mock_doc_processor, mock_session_manager, mock_ai_generator,
        mock_vector_store_class
    ):
        """Test query with existing session"""
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        mock_ai = Mock()
        mock_ai_generator.return_value = mock_ai
        mock_ai.generate_response.return_value = "Answer"

        mock_session_mgr = Mock()
        mock_session_manager.return_value = mock_session_mgr
        mock_session_mgr.get_conversation_history.return_value = "Previous: Hello"

        mock_tool_mgr = Mock()
        mock_tool_manager.return_value = mock_tool_mgr
        mock_tool_mgr.get_tool_definitions.return_value = []
        mock_tool_mgr.get_last_sources.return_value = []

        # Create RAG system and query
        rag = RAGSystem(self.config)
        response, sources = rag.query("Follow-up question", session_id="session_123")

        # Verify history was retrieved
        mock_session_mgr.get_conversation_history.assert_called_once_with("session_123")

        # Verify AI was called with history
        call_kwargs = mock_ai.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] == "Previous: Hello"

        # Verify exchange was added to history
        mock_session_mgr.add_exchange.assert_called_once_with(
            "session_123",
            "Follow-up question",
            "Answer"
        )

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.CourseSearchTool')
    @patch('rag_system.CourseOutlineTool')
    @patch('rag_system.ToolManager')
    def test_query_with_zero_results_bug(
        self, mock_tool_manager, mock_outline_tool, mock_search_tool,
        mock_doc_processor, mock_session_manager, mock_ai_generator,
        mock_vector_store_class
    ):
        """
        Test query behavior when vector store returns 0 results due to MAX_RESULTS=0 bug.
        This simulates the 'query failed' scenario.
        """
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        mock_ai = Mock()
        mock_ai_generator.return_value = mock_ai

        mock_session_mgr = Mock()
        mock_session_manager.return_value = mock_session_mgr

        mock_tool_mgr = Mock()
        mock_tool_manager.return_value = mock_tool_mgr
        mock_tool_mgr.get_tool_definitions.return_value = [
            {"name": "search_course_content", "description": "Search"}
        ]
        mock_tool_mgr.get_last_sources.return_value = []

        # Simulate AI getting no results from tool
        mock_ai.generate_response.return_value = "No relevant content found."

        # Create RAG system and query
        rag = RAGSystem(self.config)
        response, sources = rag.query("Find something")

        # Verify response
        assert response == "No relevant content found."
        assert sources == []

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.CourseSearchTool')
    @patch('rag_system.CourseOutlineTool')
    @patch('rag_system.ToolManager')
    def test_query_with_multiple_sources(
        self, mock_tool_manager, mock_outline_tool, mock_search_tool,
        mock_doc_processor, mock_session_manager, mock_ai_generator,
        mock_vector_store_class
    ):
        """Test query returns multiple sources"""
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        mock_ai = Mock()
        mock_ai_generator.return_value = mock_ai
        mock_ai.generate_response.return_value = "Here's what I found..."

        mock_session_mgr = Mock()
        mock_session_manager.return_value = mock_session_mgr

        mock_tool_mgr = Mock()
        mock_tool_manager.return_value = mock_tool_mgr
        mock_tool_mgr.get_tool_definitions.return_value = []
        mock_tool_mgr.get_last_sources.return_value = [
            {"text": "Python - Lesson 1", "link": "http://example.com/1"},
            {"text": "Python - Lesson 2", "link": "http://example.com/2"},
            {"text": "Java - Lesson 3", "link": "http://example.com/3"}
        ]

        # Create RAG system and query
        rag = RAGSystem(self.config)
        response, sources = rag.query("variables and data types")

        # Verify multiple sources are returned
        assert len(sources) == 3
        assert sources[0]["text"] == "Python - Lesson 1"
        assert sources[1]["text"] == "Python - Lesson 2"
        assert sources[2]["text"] == "Java - Lesson 3"

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.CourseSearchTool')
    @patch('rag_system.CourseOutlineTool')
    @patch('rag_system.ToolManager')
    def test_query_error_handling(
        self, mock_tool_manager, mock_outline_tool, mock_search_tool,
        mock_doc_processor, mock_session_manager, mock_ai_generator,
        mock_vector_store_class
    ):
        """Test error handling in query flow"""
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        mock_ai = Mock()
        mock_ai_generator.return_value = mock_ai
        mock_ai.generate_response.side_effect = Exception("API Error")

        mock_session_mgr = Mock()
        mock_session_manager.return_value = mock_session_mgr

        mock_tool_mgr = Mock()
        mock_tool_manager.return_value = mock_tool_mgr
        mock_tool_mgr.get_tool_definitions.return_value = []

        # Create RAG system and query - should raise exception
        rag = RAGSystem(self.config)

        with pytest.raises(Exception, match="API Error"):
            rag.query("Test query")

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.CourseSearchTool')
    @patch('rag_system.CourseOutlineTool')
    @patch('rag_system.ToolManager')
    def test_query_with_new_session(
        self, mock_tool_manager, mock_outline_tool, mock_search_tool,
        mock_doc_processor, mock_session_manager, mock_ai_generator,
        mock_vector_store_class
    ):
        """Test query creates new session when none provided"""
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        mock_ai = Mock()
        mock_ai_generator.return_value = mock_ai
        mock_ai.generate_response.return_value = "Response"

        mock_session_mgr = Mock()
        mock_session_manager.return_value = mock_session_mgr
        mock_session_mgr.get_conversation_history.return_value = None

        mock_tool_mgr = Mock()
        mock_tool_manager.return_value = mock_tool_mgr
        mock_tool_mgr.get_tool_definitions.return_value = []
        mock_tool_mgr.get_last_sources.return_value = []

        # Create RAG system and query without session_id
        rag = RAGSystem(self.config)
        response, sources = rag.query("New chat question", session_id=None)

        # Verify response
        assert response == "Response"
        assert sources == []

        # Session exchange should not be added (no session_id)
        mock_session_mgr.add_exchange.assert_not_called()


class TestRAGSystemConfiguration:
    """Test suite for RAG system configuration issues"""

    def test_max_results_zero_causes_empty_results(self):
        """
        Test that MAX_RESULTS=0 in config causes queries to return no results.
        This is the likely cause of 'query failed' errors.
        """
        # Create config with MAX_RESULTS=0 (the bug)
        bad_config = Mock(spec=Config)
        bad_config.CHROMA_PATH = "./test_chroma_db"
        bad_config.CHUNK_SIZE = 800
        bad_config.CHUNK_OVERLAP = 100
        bad_config.MAX_RESULTS = 0  # BUG: This will cause 0 results!
        bad_config.MAX_HISTORY = 2
        bad_config.ZHIPUAI_API_KEY = "test_key"

        with patch('rag_system.VectorStore') as mock_vector_store_class:
            # Track the call to VectorStore to verify max_results is passed
            mock_vector_store_class.return_value = Mock(max_results=0)

            with patch('rag_system.AIGenerator') as mock_ai_generator:
                mock_ai = Mock()
                mock_ai_generator.return_value = mock_ai

                with patch('rag_system.SessionManager') as mock_session_manager:
                    mock_session_mgr = Mock()
                    mock_session_manager.return_value = mock_session_mgr

                    with patch('rag_system.DocumentProcessor'):
                        with patch('rag_system.CourseSearchTool'):
                            with patch('rag_system.CourseOutlineTool'):
                                with patch('rag_system.ToolManager') as mock_tool_manager:
                                    mock_tool_mgr = Mock()
                                    mock_tool_manager.return_value = mock_tool_mgr
                                    mock_tool_mgr.get_tool_definitions.return_value = []
                                    mock_tool_mgr.get_last_sources.return_value = []
                                    mock_ai.generate_response.return_value = "No results"

                                    # Create RAG system with bad config
                                    rag = RAGSystem(bad_config)

                                    # The issue: VectorStore was initialized with max_results=0
                                    # This means all searches will return 0 results
                                    # Verify the call was made with max_results=0
                                    mock_vector_store_class.assert_called_once()
                                    call_kwargs = mock_vector_store_class.call_args[1]
                                    assert call_kwargs["max_results"] == 0, \
                                        "VectorStore should be called with max_results=0 from config"

    def test_vector_store_max_results_propagation(self):
        """Test that MAX_RESULTS from config propagates to VectorStore"""
        test_config = Mock(spec=Config)
        test_config.CHROMA_PATH = "./test_chroma_db"
        test_config.CHUNK_SIZE = 800
        test_config.CHUNK_OVERLAP = 100
        test_config.MAX_RESULTS = 10
        test_config.MAX_HISTORY = 2
        test_config.ZHIPUAI_API_KEY = "test_key"

        with patch('rag_system.AIGenerator'):
            with patch('rag_system.SessionManager'):
                with patch('rag_system.DocumentProcessor'):
                    with patch('rag_system.CourseSearchTool'):
                        with patch('rag_system.CourseOutlineTool'):
                            with patch('rag_system.ToolManager') as mock_tool_manager:
                                mock_tool_mgr = Mock()
                                mock_tool_manager.return_value = mock_tool_mgr
                                mock_tool_mgr.get_tool_definitions.return_value = []
                                mock_tool_mgr.get_last_sources.return_value = []

                                with patch('rag_system.VectorStore') as mock_vector_store_class:
                                    mock_vector_store = Mock()
                                    mock_vector_store_class.return_value = mock_vector_store

                                    # Create RAG system
                                    rag = RAGSystem(test_config)

                                    # Verify max_results was passed to VectorStore
                                    mock_vector_store_class.assert_called_once()
                                    call_kwargs = mock_vector_store_class.call_args[1]
                                    assert call_kwargs["max_results"] == 10


class TestRAGSystemInitialization:
    """Test suite for RAG system component initialization"""

    def setup_method(self):
        """Setup test fixtures"""
        self.config = Mock(spec=Config)
        self.config.CHROMA_PATH = "./test_chroma_db"
        self.config.CHUNK_SIZE = 800
        self.config.CHUNK_OVERLAP = 100
        self.config.MAX_RESULTS = 5
        self.config.MAX_HISTORY = 2
        self.config.ZHIPUAI_API_KEY = "test_key"
        self.config.ANTHROPIC_API_KEY = "test_key"
        self.config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
        self.config.ANTHROPIC_BASE_URL = None

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.CourseSearchTool')
    @patch('rag_system.CourseOutlineTool')
    @patch('rag_system.ToolManager')
    def test_tools_registered_on_init(
        self, mock_tool_manager, mock_outline_tool, mock_search_tool,
        mock_doc_processor, mock_session_manager, mock_ai_generator,
        mock_vector_store_class
    ):
        """Test that search and outline tools are registered on initialization"""
        # Setup mocks
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        mock_ai = Mock()
        mock_ai_generator.return_value = mock_ai

        mock_session_mgr = Mock()
        mock_session_manager.return_value = mock_session_mgr

        mock_search_instance = Mock()
        mock_search_tool.return_value = mock_search_instance

        mock_outline_instance = Mock()
        mock_outline_tool.return_value = mock_outline_instance

        mock_tool_mgr = Mock()
        mock_tool_manager.return_value = mock_tool_mgr

        # Create RAG system
        rag = RAGSystem(self.config)

        # Verify tool manager was created
        mock_tool_manager.assert_called_once()

        # Verify tools were instantiated with vector_store
        mock_search_tool.assert_called_once()
        mock_outline_tool.assert_called_once()

        # Verify tools were registered
        assert mock_tool_mgr.register_tool.call_count == 2

    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    @patch('rag_system.CourseSearchTool')
    @patch('rag_system.CourseOutlineTool')
    @patch('rag_system.ToolManager')
    def test_anthropic_base_url_passed_when_configured(
        self, mock_tool_manager, mock_outline_tool, mock_search_tool,
        mock_doc_processor, mock_session_manager, mock_ai_generator,
        mock_vector_store_class
    ):
        """Test that custom Anthropic base URL is passed when configured"""
        # Configure with custom base URL
        self.config.ANTHROPIC_BASE_URL = "https://custom.api.url"

        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        mock_ai = Mock()
        mock_ai_generator.return_value = mock_ai

        mock_session_mgr = Mock()
        mock_session_manager.return_value = mock_session_mgr

        mock_tool_mgr = Mock()
        mock_tool_manager.return_value = mock_tool_mgr

        # Create RAG system
        rag = RAGSystem(self.config)

        # Verify AIGenerator was called with base_url
        mock_ai_generator.assert_called_once()
        call_kwargs = mock_ai_generator.call_args[1]
        assert "base_url" in call_kwargs
        assert call_kwargs["base_url"] == "https://custom.api.url"
