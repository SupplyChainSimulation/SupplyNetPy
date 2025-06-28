### GlobalLogger

The `GlobalLogger` class provides a flexible logging system for the SupplyNetPy simulations. It allows logging messages to both the console and a file, and can be easily enabled or disabled during runtime.

`GlobalLogger(logger_name='sim_trace', log_to_file=True, log_file='simulation_trace.log', log_to_screen=True)`
:::SupplyNetPy.Components.logger.GlobalLogger


#### Methods
| Method | Description |
| --- | --- |
| [set_log_file](#set_log_file) | Set the log file name |
| [get_log_file](#get_log_file) | Get the current log file name |
| [set_logger](#set_logger) | Set logger name |
| [configure_logger](#configure_logger) | Configure logger handlers |
| [log](#log) | Log a message at a specified level |
| [enable_logging](#enable_logging) | Enable logging |
| [disable_logging](#disable_logging) | Disable logging |

##### set_log_file
`set_log_file(filename)`
:::SupplyNetPy.Components.logger.GlobalLogger.set_log_file

##### get_log_file
`get_log_file()`
:::SupplyNetPy.Components.logger.GlobalLogger.get_log_file

##### set_logger
`set_logger(logger_name)`
:::SupplyNetPy.Components.logger.GlobalLogger.set_logger

##### configure_logger
`configure_logger()`
:::SupplyNetPy.Components.logger.GlobalLogger.configure_logger

##### log
`log(level, message)`
:::SupplyNetPy.Components.logger.GlobalLogger.log

##### enable_logging
`enable_logging(log_to_file=True, log_to_screen=True)`
:::SupplyNetPy.Components.logger.GlobalLogger.enable_logging

##### disable_logging
`disable_logging()`
:::SupplyNetPy.Components.logger.GlobalLogger.disable_logging


