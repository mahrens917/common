"""Tests for chart_generator_helpers.chart_generator_initializer module."""

from unittest.mock import MagicMock, patch

from common.chart_generator_helpers.chart_generator_initializer import (
    ChartGeneratorInitializer,
)


class TestChartGeneratorInitializerInitializeComponents:
    """Tests for initialize_components static method."""

    def test_returns_dict(self) -> None:
        """Test returns dictionary."""
        with patch("common.chart_generator_helpers.chart_generator_initializer.ChartStyler") as mock_styler:
            mock_styler.return_value.primary_color = "blue"
            with patch("common.chart_generator_helpers.chart_generator_initializer.get_schema_config"):
                with patch("common.chart_generator_helpers.chart_generator_initializer.ChartFileManager"):
                    with patch("common.chart_generator_helpers.chart_generator_initializer.ProgressNotifier"):
                        with patch("common.chart_generator_helpers.chart_generator_initializer.TimeAxisConfigurator"):
                            with patch("common.chart_generator_helpers.chart_generator_initializer.CityTokenResolver"):
                                with patch("common.chart_generator_helpers.chart_generator_initializer.KalshiStrikeCollector"):
                                    with patch("common.chart_generator_helpers.chart_generator_initializer.LoadChartCreator"):
                                        with patch("common.chart_generator_helpers.chart_generator_initializer.SystemChartCreator"):
                                            with patch("common.chart_generator_helpers.chart_generator_initializer.PriceChartCreator"):
                                                result = ChartGeneratorInitializer.initialize_components(
                                                    price_path_calculator=MagicMock(),
                                                    prediction_horizon_days=7,
                                                    progress_callback=MagicMock(),
                                                    generate_unified_chart_func=MagicMock(),
                                                )

                                                assert isinstance(result, dict)

    def test_includes_styler(self) -> None:
        """Test includes styler in result."""
        mock_styler_instance = MagicMock()
        mock_styler_instance.primary_color = "blue"

        with patch("common.chart_generator_helpers.chart_generator_initializer.ChartStyler") as mock_styler:
            mock_styler.return_value = mock_styler_instance
            with patch("common.chart_generator_helpers.chart_generator_initializer.get_schema_config"):
                with patch("common.chart_generator_helpers.chart_generator_initializer.ChartFileManager"):
                    with patch("common.chart_generator_helpers.chart_generator_initializer.ProgressNotifier"):
                        with patch("common.chart_generator_helpers.chart_generator_initializer.TimeAxisConfigurator"):
                            with patch("common.chart_generator_helpers.chart_generator_initializer.CityTokenResolver"):
                                with patch("common.chart_generator_helpers.chart_generator_initializer.KalshiStrikeCollector"):
                                    with patch("common.chart_generator_helpers.chart_generator_initializer.LoadChartCreator"):
                                        with patch("common.chart_generator_helpers.chart_generator_initializer.SystemChartCreator"):
                                            with patch("common.chart_generator_helpers.chart_generator_initializer.PriceChartCreator"):
                                                result = ChartGeneratorInitializer.initialize_components(
                                                    price_path_calculator=MagicMock(),
                                                    prediction_horizon_days=7,
                                                    progress_callback=MagicMock(),
                                                    generate_unified_chart_func=MagicMock(),
                                                )

                                                assert result["styler"] is mock_styler_instance

    def test_includes_file_manager(self) -> None:
        """Test includes file manager in result."""
        mock_file_manager = MagicMock()

        with patch("common.chart_generator_helpers.chart_generator_initializer.ChartStyler") as mock_styler:
            mock_styler.return_value.primary_color = "blue"
            with patch("common.chart_generator_helpers.chart_generator_initializer.get_schema_config"):
                with patch("common.chart_generator_helpers.chart_generator_initializer.ChartFileManager") as mock_fm:
                    mock_fm.return_value = mock_file_manager
                    with patch("common.chart_generator_helpers.chart_generator_initializer.ProgressNotifier"):
                        with patch("common.chart_generator_helpers.chart_generator_initializer.TimeAxisConfigurator"):
                            with patch("common.chart_generator_helpers.chart_generator_initializer.CityTokenResolver"):
                                with patch("common.chart_generator_helpers.chart_generator_initializer.KalshiStrikeCollector"):
                                    with patch("common.chart_generator_helpers.chart_generator_initializer.LoadChartCreator"):
                                        with patch("common.chart_generator_helpers.chart_generator_initializer.SystemChartCreator"):
                                            with patch("common.chart_generator_helpers.chart_generator_initializer.PriceChartCreator"):
                                                result = ChartGeneratorInitializer.initialize_components(
                                                    price_path_calculator=MagicMock(),
                                                    prediction_horizon_days=7,
                                                    progress_callback=MagicMock(),
                                                    generate_unified_chart_func=MagicMock(),
                                                )

                                                assert result["file_manager"] is mock_file_manager

    def test_uses_provided_calculator(self) -> None:
        """Test uses provided price path calculator."""
        mock_calculator = MagicMock()

        with patch("common.chart_generator_helpers.chart_generator_initializer.ChartStyler") as mock_styler:
            mock_styler.return_value.primary_color = "blue"
            with patch("common.chart_generator_helpers.chart_generator_initializer.get_schema_config"):
                with patch("common.chart_generator_helpers.chart_generator_initializer.ChartFileManager"):
                    with patch("common.chart_generator_helpers.chart_generator_initializer.ProgressNotifier"):
                        with patch("common.chart_generator_helpers.chart_generator_initializer.TimeAxisConfigurator"):
                            with patch("common.chart_generator_helpers.chart_generator_initializer.CityTokenResolver"):
                                with patch("common.chart_generator_helpers.chart_generator_initializer.KalshiStrikeCollector"):
                                    with patch("common.chart_generator_helpers.chart_generator_initializer.LoadChartCreator"):
                                        with patch("common.chart_generator_helpers.chart_generator_initializer.SystemChartCreator"):
                                            with patch("common.chart_generator_helpers.chart_generator_initializer.PriceChartCreator"):
                                                result = ChartGeneratorInitializer.initialize_components(
                                                    price_path_calculator=mock_calculator,
                                                    prediction_horizon_days=7,
                                                    progress_callback=MagicMock(),
                                                    generate_unified_chart_func=MagicMock(),
                                                )

                                                assert result["price_path_calculator"] is mock_calculator

    def test_creates_calculator_when_none(self) -> None:
        """Test creates calculator when not provided."""
        with patch("common.chart_generator_helpers.chart_generator_initializer.ChartStyler") as mock_styler:
            mock_styler.return_value.primary_color = "blue"
            with patch("common.chart_generator_helpers.chart_generator_initializer.get_schema_config"):
                with patch("common.chart_generator_helpers.chart_generator_initializer.ChartFileManager"):
                    with patch("common.chart_generator_helpers.chart_generator_initializer.ProgressNotifier"):
                        with patch("common.chart_generator_helpers.chart_generator_initializer.TimeAxisConfigurator"):
                            with patch("common.chart_generator_helpers.chart_generator_initializer.CityTokenResolver"):
                                with patch("common.chart_generator_helpers.chart_generator_initializer.KalshiStrikeCollector"):
                                    with patch("common.chart_generator_helpers.chart_generator_initializer.LoadChartCreator"):
                                        with patch("common.chart_generator_helpers.chart_generator_initializer.SystemChartCreator"):
                                            with patch("common.chart_generator_helpers.chart_generator_initializer.PriceChartCreator"):
                                                with patch(
                                                    "common.chart_generator_helpers.chart_generator_initializer.MostProbablePricePathCalculator"
                                                ) as mock_calc:
                                                    mock_calc.return_value = MagicMock()
                                                    result = ChartGeneratorInitializer.initialize_components(
                                                        price_path_calculator=None,
                                                        prediction_horizon_days=14,
                                                        progress_callback=MagicMock(),
                                                        generate_unified_chart_func=MagicMock(),
                                                    )

                                                    assert "price_path_calculator" in result

    def test_includes_horizon_days(self) -> None:
        """Test includes prediction horizon days."""
        with patch("common.chart_generator_helpers.chart_generator_initializer.ChartStyler") as mock_styler:
            mock_styler.return_value.primary_color = "blue"
            with patch("common.chart_generator_helpers.chart_generator_initializer.get_schema_config"):
                with patch("common.chart_generator_helpers.chart_generator_initializer.ChartFileManager"):
                    with patch("common.chart_generator_helpers.chart_generator_initializer.ProgressNotifier"):
                        with patch("common.chart_generator_helpers.chart_generator_initializer.TimeAxisConfigurator"):
                            with patch("common.chart_generator_helpers.chart_generator_initializer.CityTokenResolver"):
                                with patch("common.chart_generator_helpers.chart_generator_initializer.KalshiStrikeCollector"):
                                    with patch("common.chart_generator_helpers.chart_generator_initializer.LoadChartCreator"):
                                        with patch("common.chart_generator_helpers.chart_generator_initializer.SystemChartCreator"):
                                            with patch("common.chart_generator_helpers.chart_generator_initializer.PriceChartCreator"):
                                                result = ChartGeneratorInitializer.initialize_components(
                                                    price_path_calculator=MagicMock(),
                                                    prediction_horizon_days=30,
                                                    progress_callback=MagicMock(),
                                                    generate_unified_chart_func=MagicMock(),
                                                )

                                                assert result["price_path_horizon_days"] == 30

    def test_includes_chart_creators(self) -> None:
        """Test includes chart creators."""
        mock_load_creator = MagicMock()
        mock_system_creator = MagicMock()
        mock_price_creator = MagicMock()

        with patch("common.chart_generator_helpers.chart_generator_initializer.ChartStyler") as mock_styler:
            mock_styler.return_value.primary_color = "blue"
            with patch("common.chart_generator_helpers.chart_generator_initializer.get_schema_config"):
                with patch("common.chart_generator_helpers.chart_generator_initializer.ChartFileManager"):
                    with patch("common.chart_generator_helpers.chart_generator_initializer.ProgressNotifier"):
                        with patch("common.chart_generator_helpers.chart_generator_initializer.TimeAxisConfigurator"):
                            with patch("common.chart_generator_helpers.chart_generator_initializer.CityTokenResolver"):
                                with patch("common.chart_generator_helpers.chart_generator_initializer.KalshiStrikeCollector"):
                                    with patch("common.chart_generator_helpers.chart_generator_initializer.LoadChartCreator") as mock_lc:
                                        mock_lc.return_value = mock_load_creator
                                        with patch(
                                            "common.chart_generator_helpers.chart_generator_initializer.SystemChartCreator"
                                        ) as mock_sc:
                                            mock_sc.return_value = mock_system_creator
                                            with patch(
                                                "common.chart_generator_helpers.chart_generator_initializer.PriceChartCreator"
                                            ) as mock_pc:
                                                mock_pc.return_value = mock_price_creator
                                                result = ChartGeneratorInitializer.initialize_components(
                                                    price_path_calculator=MagicMock(),
                                                    prediction_horizon_days=7,
                                                    progress_callback=MagicMock(),
                                                    generate_unified_chart_func=MagicMock(),
                                                )

                                                assert result["load_chart_creator"] is mock_load_creator
                                                assert result["system_chart_creator"] is mock_system_creator
                                                assert result["price_chart_creator"] is mock_price_creator
