"""
Notification tasks
"""

from typing import Dict, Any
from prefect import task, get_run_logger


@task
async def send_completion_notification(
    flow_name: str,
    result: Dict[str, Any],
    success: bool
) -> bool:
    """
    Send notification about flow completion
    """
    logger = get_run_logger()
    
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"Notification: {flow_name} {status}")
    
    if success:
        logger.info(f"Flow completed successfully: {result}")
    else:
        logger.error(f"Flow failed: {result}")
    
    # In real implementation, this would:
    # 1. Send email notifications
    # 2. Post to Slack/Teams
    # 3. Update monitoring dashboards
    # 4. Create alerts if needed
    
    return True