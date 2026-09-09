"""
Unit tests for UI resource cleanup.

Tests that heavy UI resources (QWebEngineView, timers, web channels) have proper
cleanup methods implemented.

Validates: Requirement 10.7
"""

import pytest
import inspect


class TestCleanupMethodsExist:
    """Test that cleanup methods are properly defined in UI components."""

    def test_map_widget_has_closeevent(self):
        """Test that MapWidget has closeEvent method for cleanup."""
        from modbuspython.ui.map_widget import MapWidget

        # Verify closeEvent method exists
        assert hasattr(MapWidget, "closeEvent")
        assert callable(getattr(MapWidget, "closeEvent"))

        # Verify it's not just the inherited default
        source = inspect.getsource(MapWidget.closeEvent)
        assert "Clean up QWebEngineView resources" in source or "cleanup" in source.lower()

    def test_location_tab_has_cleanup(self):
        """Test that LocationTab has cleanup method."""
        from modbuspython.ui.location_tab_fixed import LocationTab

        # Verify cleanup method exists
        assert hasattr(LocationTab, "cleanup")
        assert callable(getattr(LocationTab, "cleanup"))

        # Verify it has proper implementation
        source = inspect.getsource(LocationTab.cleanup)
        assert "visor3d" in source or "3D" in source
        assert "timer" in source.lower()

    def test_location_tab_has_closeevent(self):
        """Test that LocationTab has closeEvent that calls cleanup."""
        from modbuspython.ui.location_tab_fixed import LocationTab

        # Verify closeEvent method exists
        assert hasattr(LocationTab, "closeEvent")
        assert callable(getattr(LocationTab, "closeEvent"))

        # Verify it calls cleanup
        source = inspect.getsource(LocationTab.closeEvent)
        assert "cleanup" in source

    def test_diagnostic_tab_has_cleanup(self):
        """Test that DiagnosticTab has cleanup method."""
        from modbuspython.ui.diagnostic_tab import DiagnosticTab

        # Verify cleanup method exists
        assert hasattr(DiagnosticTab, "cleanup")
        assert callable(getattr(DiagnosticTab, "cleanup"))

        # Verify it handles timer
        source = inspect.getsource(DiagnosticTab.cleanup)
        assert "timer" in source.lower()

    def test_main_window_closeevent_calls_tab_cleanup(self):
        """Test that MainWindow closeEvent calls cleanup on tabs."""
        from modbuspython.main_app import MainWindow

        # Verify closeEvent method exists
        assert hasattr(MainWindow, "closeEvent")
        assert callable(getattr(MainWindow, "closeEvent"))

        # Verify it iterates through tabs and calls cleanup
        source = inspect.getsource(MainWindow.closeEvent)
        assert "cleanup" in source
        assert "tabs" in source.lower()


class TestCleanupImplementationDetails:
    """Test specific implementation details of cleanup methods."""

    def test_map_widget_cleanup_handles_webengine(self):
        """Test that MapWidget cleanup properly handles QWebEngineView."""
        from modbuspython.ui.map_widget import MapWidget

        # Check the cleanup method (where the actual cleanup logic is)
        source = inspect.getsource(MapWidget.cleanup)

        # Should check for webengine availability
        assert "_webengine_available" in source or "webview" in source

        # Should call stop() to stop loading
        assert "stop()" in source

        # Should set blank HTML to release resources
        assert "setHtml" in source

        # Should call deleteLater
        assert "deleteLater" in source

    def test_location_tab_cleanup_handles_3d_viewer(self):
        """Test that LocationTab cleanup properly handles 3D viewer."""
        from modbuspython.ui.location_tab_fixed import LocationTab

        source = inspect.getsource(LocationTab.cleanup)

        # Should handle visor3d (3D viewer)
        assert "visor3d" in source

        # Should stop loading
        assert "stop()" in source

        # Should set blank HTML
        assert "setHtml" in source

        # Should call deleteLater
        assert "deleteLater" in source

    def test_location_tab_cleanup_handles_web_channel(self):
        """Test that LocationTab cleanup properly handles web channel."""
        from modbuspython.ui.location_tab_fixed import LocationTab

        source = inspect.getsource(LocationTab.cleanup)

        # Should handle web_channel
        assert "web_channel" in source

        # Should deregister objects
        assert "deregisterObject" in source or "deleteLater" in source

        # Should handle pyjs bridge
        assert "pyjs" in source

    def test_location_tab_cleanup_handles_timer(self):
        """Test that LocationTab cleanup properly handles timer."""
        from modbuspython.ui.location_tab_fixed import LocationTab

        source = inspect.getsource(LocationTab.cleanup)

        # Should handle _auto_time_timer
        assert "_auto_time_timer" in source or "timer" in source.lower()

        # Should stop timer
        assert "stop()" in source

        # Should call deleteLater
        assert "deleteLater" in source

    def test_diagnostic_tab_cleanup_handles_timer(self):
        """Test that DiagnosticTab cleanup properly handles timer."""
        from modbuspython.ui.diagnostic_tab import DiagnosticTab

        source = inspect.getsource(DiagnosticTab.cleanup)

        # Should handle timer
        assert "timer" in source.lower()

        # Should stop timer
        assert "stop()" in source

        # Should call deleteLater
        assert "deleteLater" in source

    def test_cleanup_methods_have_error_handling(self):
        """Test that cleanup methods have proper error handling."""
        from modbuspython.ui.map_widget import MapWidget
        from modbuspython.ui.location_tab_fixed import LocationTab
        from modbuspython.ui.diagnostic_tab import DiagnosticTab

        # All cleanup methods should have try/except blocks
        for cls in [MapWidget, LocationTab, DiagnosticTab]:
            if hasattr(cls, "cleanup"):
                source = inspect.getsource(cls.cleanup)
            elif hasattr(cls, "closeEvent"):
                source = inspect.getsource(cls.closeEvent)
            else:
                continue

            # Should have error handling
            assert "try:" in source
            assert "except" in source

            # Should log errors
            assert "logger" in source.lower() or "error" in source.lower()


class TestRequirementValidation:
    """Test that implementation satisfies Requirement 10.7."""

    def test_requirement_10_7_qwebengineview_cleanup(self):
        """
        Requirement 10.7: WHEN QWebEngineView is destroyed,
        THE Sistema_SolarSense SHALL release associated resources.
        """
        from modbuspython.ui.map_widget import MapWidget
        from modbuspython.ui.location_tab_fixed import LocationTab

        # MapWidget uses QWebEngineView and must clean it up
        map_source = inspect.getsource(MapWidget.cleanup)
        assert "webview" in map_source
        assert "deleteLater" in map_source

        # LocationTab uses QWebEngineView (visor3d) and must clean it up
        loc_source = inspect.getsource(LocationTab.cleanup)
        assert "visor3d" in loc_source
        assert "deleteLater" in loc_source

    def test_main_window_orchestrates_cleanup(self):
        """Test that MainWindow properly orchestrates cleanup of all tabs."""
        from modbuspython.main_app import MainWindow

        source = inspect.getsource(MainWindow.closeEvent)

        # Should iterate through all tabs
        assert "tabs" in source.lower()
        assert "range" in source or "for" in source

        # Should call cleanup on tabs that have it
        assert "cleanup" in source
        assert "hasattr" in source

        # Should handle errors gracefully
        assert "try:" in source
        assert "except" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
