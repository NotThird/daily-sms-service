import click
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Recipient
from .user_config_service import UserConfigService

def get_db_session():
    """Get database session."""
    database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/sms_app')
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

@click.group()
def cli():
    """CLI tool for managing user configurations."""
    pass

@cli.command()
@click.option('--phone', prompt='Phone number', help='User phone number (e.g., +1234567890)')
@click.option('--name', prompt='Name', help='User name')
@click.option('--timezone', prompt='Timezone', default='UTC', help='User timezone')
@click.option('--style', prompt='Communication style', type=click.Choice(['casual', 'professional', 'friendly'], case_sensitive=False))
@click.option('--topics', prompt='Preferred topics (comma-separated)', help='E.g., motivation,health,mindfulness')
@click.option('--occupation', prompt='Occupation', help='User occupation')
@click.option('--hobbies', prompt='Hobbies (comma-separated)', help='E.g., reading,hiking,gaming')
def configure(phone, name, timezone, style, topics, occupation, hobbies):
    """Configure a user with all their details in one go."""
    session = get_db_session()
    user_config_service = UserConfigService(session)

    try:
        # Create or get recipient
        recipient = session.query(Recipient).filter_by(phone_number=phone).first()
        if not recipient:
            recipient = Recipient(
                phone_number=phone,
                timezone=timezone,
                is_active=True
            )
            session.add(recipient)
            session.flush()
            click.echo(f"Created new recipient: {phone}")
        else:
            click.echo(f"Found existing recipient: {phone}")

        # Prepare preferences and personal info
        topics_list = [t.strip() for t in topics.split(',')]
        hobbies_list = [h.strip() for h in hobbies.split(',')]
        
        preferences = {
            'style': style,
            'topics': topics_list
        }
        
        personal_info = {
            'occupation': occupation,
            'hobbies': hobbies_list
        }

        # Update user config with all information
        config = user_config_service.create_or_update_config(
            recipient_id=recipient.id,
            name=name,
            preferences=preferences,
            personal_info=personal_info
        )
        
        session.commit()
        
        # Show the configuration
        click.echo("\nUser configured successfully!")
        click.echo("="*50)
        click.echo(f"Phone: {phone}")
        click.echo(f"Name: {name}")
        click.echo(f"Timezone: {timezone}")
        click.echo("\nPreferences:")
        click.echo(f"  Style: {style}")
        click.echo(f"  Topics: {', '.join(topics_list)}")
        click.echo("\nPersonal Info:")
        click.echo(f"  Occupation: {occupation}")
        click.echo(f"  Hobbies: {', '.join(hobbies_list)}")
        click.echo("="*50)

    except Exception as e:
        session.rollback()
        click.echo(f"Error: {str(e)}", err=True)
    finally:
        session.close()

@cli.command()
@click.option('--phone', help='Filter by phone number (optional)')
def list_users(phone):
    """List all configured users or search by phone number."""
    session = get_db_session()
    user_config_service = UserConfigService(session)

    try:
        query = session.query(Recipient)
        if phone:
            query = query.filter(Recipient.phone_number.like(f"%{phone}%"))

        recipients = query.all()
        if not recipients:
            click.echo("No users found")
            return

        for recipient in recipients:
            config = user_config_service.get_config(recipient.id)
            click.echo("\n" + "="*50)
            click.echo(f"Phone: {recipient.phone_number}")
            click.echo(f"Active: {recipient.is_active}")
            click.echo(f"Timezone: {recipient.timezone}")
            
            if config:
                click.echo(f"Name: {config.name or 'Not set'}")
                if config.preferences:
                    click.echo("\nPreferences:")
                    for k, v in config.preferences.items():
                        if isinstance(v, list):
                            click.echo(f"  {k}: {', '.join(v)}")
                        else:
                            click.echo(f"  {k}: {v}")
                if config.personal_info:
                    click.echo("\nPersonal Info:")
                    for k, v in config.personal_info.items():
                        if isinstance(v, list):
                            click.echo(f"  {k}: {', '.join(v)}")
                        else:
                            click.echo(f"  {k}: {v}")
            click.echo("="*50)

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
    finally:
        session.close()

if __name__ == '__main__':
    cli()
