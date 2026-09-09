"""Unit tests for extracted UI widgets.

Tests for LocationSetupTab, SolarTrackerTab, and ManualControlPanel
extracted from location_tab_fixed.py during refactoring.

Uses inspection-based testing to verify widget structure and behavior
without requiring a full Qt application instance.

Validates: Requirement 15.2
"""

import pytest
import inspect
import datetime


class TestSolarTrackerTab:
    """Test automatic solar angle calculation tab."""

    def test_widget_class_exists(self):
        """Test SolarTrackerTab class can be imported."""
        from modbuspython.ui.solar_tracker_tab import SolarTrackerTab

        assert SolarTrackerTab is not None
        assert inspect.isclass(SolarTrackerTab)

    def test_widget_has_required_attributes(self):
        """Test SolarTrackerTab has expected UI attributes after initialization."""
        from modbuspython.ui.solar_tracker_tab import SolarTrackerTab

        source = inspect.getsource(SolarTrackerTab._build_ui)

        assert "lat_spin" in source
        assert "lon_spin" in source
        assert "dia_spin" in source
        assert "hora_spin" in source
        assert "hra_val" in source
        assert "dec_val" in source
        assert "alt_val" in source
        assert "az_val" in source

    def test_widget_has_calculation_methods(self):
        """Test SolarTrackerTab has calculation update method."""
        from modbuspython.ui.solar_tracker_tab import SolarTrackerTab

        assert hasattr(SolarTrackerTab, "_update_calculations")
        assert callable(getattr(SolarTrackerTab, "_update_calculations"))

    def test_widget_signals_connected(self):
        """Test SolarTrackerTab connects input signals to calculations."""
        from modbuspython.ui.solar_tracker_tab import SolarTrackerTab

        source = inspect.getsource(SolarTrackerTab._connect_signals)

        assert "valueChanged" in source
        assert "_update_calculations" in source
        assert "lat_spin" in source
        assert "lon_spin" in source
        assert "dia_spin" in source
        assert "hora_spin" in source

    def test_uses_solar_calcs_module(self):
        """Test SolarTrackerTab imports solar calculation functions."""
        from modbuspython.ui import solar_tracker_tab

        module_source = inspect.getsource(solar_tracker_tab)

        assert "calculate_hra" in module_source
        assert "calculate_decl" in module_source
        assert "calculate_alt" in module_source
        assert "calculate_az" in module_source

    def test_hour_range_in_source(self):
        """Test SolarTrackerTab sets correct hour range (0-24)."""
        from modbuspython.ui.solar_tracker_tab import SolarTrackerTab

        source = inspect.getsource(SolarTrackerTab._build_ui)

        assert "setRange(0, 24)" in source or "setRange(0,  24)" in source


class TestLocationSetupTab:
    """Test location setup tab with map and search."""

    def test_widget_class_exists(self):
        """Test LocationSetupTab class can be imported."""
        from modbuspython.ui.location_setup_tab import LocationSetupTab

        assert LocationSetupTab is not None
        assert inspect.isclass(LocationSetupTab)

    def test_widget_has_coordinates_applied_signal(self):
        """Test LocationSetupTab defines coordinates_applied signal."""
        from modbuspython.ui.location_setup_tab import LocationSetupTab

        assert hasattr(LocationSetupTab, "coordinates_applied")

    def test_widget_has_coordinate_inputs(self):
        """Test LocationSetupTab builds latitude and longitude inputs."""
        from modbuspython.ui.location_setup_tab import LocationSetupTab

        left_source = inspect.getsource(LocationSetupTab._build_left_panel)
        right_source = inspect.getsource(LocationSetupTab._build_right_panel)
        combined = left_source + right_source

        assert "lat_display" in combined
        assert "lon_display" in combined

    def test_widget_has_search_functionality(self):
        """Test LocationSetupTab builds search input and button."""
        from modbuspython.ui.location_setup_tab import LocationSetupTab

        source = inspect.getsource(LocationSetupTab._build_controls_panel)

        assert "search_input" in source
        assert "search_btn" in source

    def test_widget_uses_map_widget(self):
        """Test LocationSetupTab imports and uses MapWidget."""
        from modbuspython.ui import location_setup_tab

        module_source = inspect.getsource(location_setup_tab)

        assert "MapWidget" in module_source

    def test_sync_from_calculation_method(self):
        """Test LocationSetupTab has sync_from_calculation method."""
        from modbuspython.ui.location_setup_tab import LocationSetupTab

        assert hasattr(LocationSetupTab, "sync_from_calculation")
        assert callable(getattr(LocationSetupTab, "sync_from_calculation"))

        source = inspect.getsource(LocationSetupTab.sync_from_calculation)
        assert "lat_display" in source
        assert "lon_display" in source

    def test_has_geocoding_search_method(self):
        """Test LocationSetupTab has _search_location method."""
        from modbuspython.ui.location_setup_tab import LocationSetupTab

        assert hasattr(LocationSetupTab, "_search_location")
        assert callable(getattr(LocationSetupTab, "_search_location"))


class TestManualControlPanel:
    """Test manual control panel with angle controls."""

    def test_widget_class_exists(self):
        """Test ManualControlPanel class can be imported."""
        from modbuspython.ui.manual_control_panel import ManualControlPanel

        assert ManualControlPanel is not None
        assert inspect.isclass(ManualControlPanel)

    def test_widget_has_angle_controls(self):
        """Test ManualControlPanel builds rotation and elevation controls."""
        from modbuspython.ui.manual_control_panel import ManualControlPanel

        source = inspect.getsource(ManualControlPanel._build_controls_panel)

        assert "rot_spin" in source
        assert "rot_slider" in source
        assert "elev_spin" in source
        assert "elev_slider" in source

    def test_rotation_range(self):
        """Test ManualControlPanel sets rotation range to 0-360."""
        from modbuspython.ui.manual_control_panel import ManualControlPanel

        source = inspect.getsource(ManualControlPanel._build_controls_panel)

        assert "setRange(0, 360)" in source or "setRange(0,  360)" in source

    def test_elevation_range(self):
        """Test ManualControlPanel sets elevation range to 0-145."""
        from modbuspython.ui.manual_control_panel import ManualControlPanel

        source = inspect.getsource(ManualControlPanel._build_controls_panel)

        assert "setRange(0, 145)" in source or "setRange(0,  145)" in source

    def test_widget_has_send_command_method(self):
        """Test ManualControlPanel has _send_manual_command method."""
        from modbuspython.ui.manual_control_panel import ManualControlPanel

        assert hasattr(ManualControlPanel, "_send_manual_command")
        assert callable(getattr(ManualControlPanel, "_send_manual_command"))

    def test_send_command_validates_angles(self):
        """Test _send_manual_command calls validation service."""
        from modbuspython.ui.manual_control_panel import ManualControlPanel

        source = inspect.getsource(ManualControlPanel._send_manual_command)

        assert "validate_rotation" in source
        assert "validate_elevation" in source

    def test_widget_has_cleanup_method(self):
        """Test ManualControlPanel has cleanup_3d_viewer method."""
        from modbuspython.ui.manual_control_panel import ManualControlPanel

        assert hasattr(ManualControlPanel, "cleanup_3d_viewer")
        assert callable(getattr(ManualControlPanel, "cleanup_3d_viewer"))

    def test_widget_has_sync_widgets_method(self):
        """Test ManualControlPanel has _sync_widgets method."""
        from modbuspython.ui.manual_control_panel import ManualControlPanel

        assert hasattr(ManualControlPanel, "_sync_widgets")
        assert callable(getattr(ManualControlPanel, "_sync_widgets"))

        source = inspect.getsource(ManualControlPanel._sync_widgets)
        assert "rot_spin" in source
        assert "elev_spin" in source
        assert "rot_slider" in source
        assert "elev_slider" in source

    def test_widget_uses_web_engine_view(self):
        """Test ManualControlPanel uses QWebEngineView for 3D viewer."""
        from modbuspython.ui import manual_control_panel

        module_source = inspect.getsource(manual_control_panel)

        assert "QWebEngineView" in module_source

    def test_widget_has_web_channel_setup(self):
        """Test ManualControlPanel has setup_web_channel method."""
        from modbuspython.ui.manual_control_panel import ManualControlPanel

        assert hasattr(ManualControlPanel, "setup_web_channel")
        assert callable(getattr(ManualControlPanel, "setup_web_channel"))


class TestWidgetImportCompatibility:
    """Test that extracted widgets can be imported correctly."""

    def test_location_setup_tab_import(self):
        """Test LocationSetupTab can be imported from ui module."""
        from modbuspython.ui.location_setup_tab import LocationSetupTab

        assert LocationSetupTab is not None

    def test_solar_tracker_tab_import(self):
        """Test SolarTrackerTab can be imported from ui module."""
        from modbuspython.ui.solar_tracker_tab import SolarTrackerTab

        assert SolarTrackerTab is not None

    def test_manual_control_panel_import(self):
        """Test ManualControlPanel can be imported from ui module."""
        from modbuspython.ui.manual_control_panel import ManualControlPanel

        assert ManualControlPanel is not None

    def test_pyjs_bridge_import(self):
        """Test PyJsBridge can be imported from ui module."""
        from modbuspython.ui.pyjs_bridge import PyJsBridge

        assert PyJsBridge is not None

    def test_location_tab_composes_widgets(self):
        """Test LocationTab imports and uses extracted widgets."""
        from modbuspython.ui import location_tab_fixed

        source = inspect.getsource(location_tab_fixed)

        assert "LocationSetupTab" in source
        assert "SolarTrackerTab" in source
        assert "ManualControlPanel" in source
        assert "PyJsBridge" in source

    def test_extracted_modules_have_docstrings(self):
        """Test all extracted modules have docstrings."""
        from modbuspython.ui import (
            location_setup_tab,
            solar_tracker_tab,
            manual_control_panel,
            pyjs_bridge,
        )

        assert location_setup_tab.__doc__ is not None
        assert solar_tracker_tab.__doc__ is not None
        assert manual_control_panel.__doc__ is not None
        assert pyjs_bridge.__doc__ is not None

    def test_extracted_classes_have_docstrings(self):
        """Test all extracted classes have docstrings."""
        from modbuspython.ui.location_setup_tab import LocationSetupTab
        from modbuspython.ui.solar_tracker_tab import SolarTrackerTab
        from modbuspython.ui.manual_control_panel import ManualControlPanel
        from modbuspython.ui.pyjs_bridge import PyJsBridge

        assert LocationSetupTab.__doc__ is not None
        assert SolarTrackerTab.__doc__ is not None
        assert ManualControlPanel.__doc__ is not None
        assert PyJsBridge.__doc__ is not None
