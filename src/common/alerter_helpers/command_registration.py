"""Command registration helper for Alerter."""


class CommandRegistration:
    """Handles command registration for Alerter."""

    @staticmethod
    def register_commands(command_registry, command_coordinator) -> None:
        """
        Register all command handlers.

        Args:
            command_registry: Registry to register commands with
            command_coordinator: Coordinator containing command handlers
        """
        command_registry.register_command_handler("help", command_coordinator.handle_help)
        command_registry.register_command_handler("load", command_coordinator.handle_load)
        command_registry.register_command_handler("price", command_coordinator.handle_price)
        command_registry.register_command_handler("temp", command_coordinator.handle_temp)
        command_registry.register_command_handler("pnl", command_coordinator.handle_pnl)
