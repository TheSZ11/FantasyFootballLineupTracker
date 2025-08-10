"""
Configuration management CLI tool.

Provides command-line utilities for configuration setup, validation,
and template generation to simplify deployment and maintenance.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

from .config_loader import ConfigurationLoader, load_config
from .app_config import AppConfig
from ..domain.exceptions import ConfigurationError
from ..utils.logging import configure_logging, get_logger


def setup_cli_logging():
    """Setup basic logging for CLI operations."""
    configure_logging(
        log_level="INFO",
        enable_console=True,
        structured_format=False
    )


def validate_config_command(args):
    """Validate configuration command."""
    logger = get_logger(__name__)
    
    try:
        if args.config_file:
            # Validate config file
            loader = ConfigurationLoader()
            errors = loader.validate_config_file(args.config_file)
            
            if errors:
                print("❌ Configuration validation failed:")
                for error in errors:
                    print(f"   - {error}")
                return False
            else:
                print("✅ Configuration file is valid")
                return True
        else:
            # Validate current environment configuration
            config = load_config(
                env_file=args.env_file,
                validate_runtime=args.runtime_check
            )
            
            print("✅ Configuration loaded and validated successfully")
            print(f"\n{config.get_summary()}")
            return True
            
    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.error(f"Configuration validation failed: {e}")
        return False


def generate_template_command(args):
    """Generate configuration template command."""
    logger = get_logger(__name__)
    
    try:
        loader = ConfigurationLoader()
        
        if args.format == 'env':
            # Generate .env template
            output_file = args.output or f".env.{args.environment}"
            loader.export_env_template(output_file, args.environment)
            print(f"✅ Environment template generated: {output_file}")
            
        elif args.format == 'json':
            # Generate JSON template
            template = loader.get_config_template(args.environment)
            output_file = args.output or f"config.{args.environment}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2)
            
            print(f"✅ JSON configuration template generated: {output_file}")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate template: {e}")
        logger.error(f"Template generation failed: {e}")
        return False


def check_command(args):
    """Configuration health check command."""
    logger = get_logger(__name__)
    
    try:
        config = load_config(
            env_file=args.env_file,
            validate_runtime=True
        )
        
        print("🔍 Running configuration health check...\n")
        
        # Basic information
        print(f"📋 Configuration Summary:")
        print(f"   Environment: {config.environment}")
        print(f"   Debug Mode: {config.debug_mode}")
        print(f"   Timezone: {config.user_timezone}")
        print()
        
        # Check API settings
        print(f"📡 API Configuration:")
        print(f"   Base URL: {config.api_settings.base_url}")
        print(f"   Timeout: {config.api_settings.timeout_seconds}s")
        print(f"   Max Retries: {config.api_settings.max_retries}")
        print(f"   Rate Limit: {config.api_settings.rate_limit_per_minute}/min")
        print()
        
        # Check notification providers
        print(f"📬 Notification Providers:")
        email_status = "✅ Configured" if config.notification_settings.email_enabled else "❌ Not configured"
        discord_status = "✅ Configured" if config.notification_settings.discord_enabled else "❌ Not configured"
        print(f"   Email: {email_status}")
        print(f"   Discord: {discord_status}")
        
        if not config.notification_settings.email_enabled and not config.notification_settings.discord_enabled:
            print("   ⚠️  Warning: No notification providers configured")
        print()
        
        # Check files
        print(f"📁 File Configuration:")
        squad_file = Path(config.monitoring_settings.squad_file_path)
        squad_status = "✅ Exists" if squad_file.exists() else "❌ Not found"
        print(f"   Squad File: {squad_file} ({squad_status})")
        
        if config.monitoring_settings.backup_squad_file_path:
            backup_file = Path(config.monitoring_settings.backup_squad_file_path)
            backup_status = "✅ Exists" if backup_file.exists() else "❌ Not found"
            print(f"   Backup File: {backup_file} ({backup_status})")
        
        if config.logging_settings.log_file:
            log_file = Path(config.logging_settings.log_file)
            log_dir = log_file.parent
            log_status = "✅ Directory exists" if log_dir.exists() else "❌ Directory missing"
            print(f"   Log File: {log_file} ({log_status})")
        print()
        
        # Check runtime requirements
        print(f"🔧 Runtime Requirements:")
        runtime_issues = config.validate_runtime_requirements()
        
        if runtime_issues:
            print("   ❌ Issues found:")
            for issue in runtime_issues:
                print(f"      - {issue}")
        else:
            print("   ✅ All requirements satisfied")
        print()
        
        # Overall status
        has_notifications = config.notification_settings.email_enabled or config.notification_settings.discord_enabled
        has_squad_file = squad_file.exists()
        no_runtime_issues = len(runtime_issues) == 0
        
        if has_notifications and has_squad_file and no_runtime_issues:
            print("🎉 Configuration health check passed!")
            print("   Your LineupTracker is ready to run.")
            return True
        else:
            print("⚠️  Configuration health check found issues.")
            print("   Please address the issues above before running LineupTracker.")
            return False
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        logger.error(f"Configuration health check failed: {e}")
        return False


def init_command(args):
    """Initialize configuration command."""
    logger = get_logger(__name__)
    
    try:
        print("🚀 Initializing LineupTracker configuration...\n")
        
        # Determine environment
        environment = args.environment or 'production'
        
        # Check if .env already exists
        env_file = Path('.env')
        if env_file.exists() and not args.force:
            print(f"❌ .env file already exists. Use --force to overwrite.")
            return False
        
        # Generate .env template
        loader = ConfigurationLoader()
        loader.export_env_template('.env', environment)
        
        print(f"✅ Configuration template generated: .env")
        print(f"   Environment: {environment}")
        print()
        print("📝 Next steps:")
        print("   1. Edit .env file with your settings")
        print("   2. Configure notification providers (Discord/Email)")
        print("   3. Ensure your squad file (my_roster.csv) is present")
        print("   4. Run 'python -m src.lineup_tracker.config.config_cli check' to validate")
        print()
        print("💡 Key settings to configure in .env:")
        print("   - DISCORD_WEBHOOK_URL (for Discord notifications)")
        print("   - EMAIL_* settings (for email notifications)")
        print("   - SQUAD_FILE_PATH (path to your Fantrax CSV)")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        logger.error(f"Configuration initialization failed: {e}")
        return False


def show_command(args):
    """Show current configuration command."""
    logger = get_logger(__name__)
    
    try:
        config = load_config(
            env_file=args.env_file,
            validate_runtime=False
        )
        
        if args.format == 'summary':
            print(config.get_summary())
        elif args.format == 'json':
            config_dict = config.to_dict()
            
            # Mask sensitive values
            if 'notification_settings' in config_dict:
                if config_dict['notification_settings'].get('email'):
                    config_dict['notification_settings']['email']['password'] = "***masked***"
                if config_dict['notification_settings'].get('discord'):
                    webhook_url = config_dict['notification_settings']['discord']['webhook_url']
                    if webhook_url:
                        # Mask the webhook token
                        parts = webhook_url.split('/')
                        if len(parts) >= 2:
                            parts[-1] = "***masked***"
                            config_dict['notification_settings']['discord']['webhook_url'] = '/'.join(parts)
            
            print(json.dumps(config_dict, indent=2))
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to show configuration: {e}")
        logger.error(f"Show configuration failed: {e}")
        return False


def main():
    """Main CLI entry point."""
    setup_cli_logging()
    
    parser = argparse.ArgumentParser(
        description="LineupTracker Configuration Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.lineup_tracker.config.config_cli init
  python -m src.lineup_tracker.config.config_cli check
  python -m src.lineup_tracker.config.config_cli validate --env-file .env
  python -m src.lineup_tracker.config.config_cli template --environment development
  python -m src.lineup_tracker.config.config_cli show --format json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize configuration')
    init_parser.add_argument('--environment', choices=['development', 'staging', 'production'],
                           default='production', help='Target environment')
    init_parser.add_argument('--force', action='store_true',
                           help='Overwrite existing configuration files')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument('--env-file', help='Path to .env file')
    validate_parser.add_argument('--config-file', help='Path to JSON/YAML config file')
    validate_parser.add_argument('--no-runtime-check', dest='runtime_check', 
                                action='store_false', default=True,
                                help='Skip runtime requirement checks')
    
    # Template command  
    template_parser = subparsers.add_parser('template', help='Generate configuration template')
    template_parser.add_argument('--environment', choices=['development', 'staging', 'production'],
                                default='production', help='Target environment')
    template_parser.add_argument('--format', choices=['env', 'json'], default='env',
                                help='Template format')
    template_parser.add_argument('--output', help='Output file path')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Run configuration health check')
    check_parser.add_argument('--env-file', help='Path to .env file')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show current configuration')
    show_parser.add_argument('--env-file', help='Path to .env file')
    show_parser.add_argument('--format', choices=['summary', 'json'], default='summary',
                           help='Output format')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    success = False
    
    if args.command == 'init':
        success = init_command(args)
    elif args.command == 'validate':
        success = validate_config_command(args)
    elif args.command == 'template':
        success = generate_template_command(args)
    elif args.command == 'check':
        success = check_command(args)
    elif args.command == 'show':
        success = show_command(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
