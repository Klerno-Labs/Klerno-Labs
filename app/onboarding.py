"""
Onboarding and User Experience Module for Klerno Labs
Provides guided onboarding, in - app tutorials, and user experience enhancements
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from enum import Enum
import json
from datetime import datetime


class OnboardingStep(str, Enum):
    """Enumeration of onboarding steps"""
    WELCOME="welcome"
    API_KEY_SETUP="api_key_setup"
    FIRST_TRANSACTION="first_transaction"
    DASHBOARD_TOUR="dashboard_tour"
    ALERTS_SETUP="alerts_setup"
    SETTINGS_CONFIG="settings_config"
    COMPLETED="completed"


class GuideType(str, Enum):
    """Types of in - app guides"""
    ONBOARDING="onboarding"
    FEATURE_INTRO="feature_intro"
    QUICK_TIP="quick_tip"
    BEST_PRACTICE="best_practice"


class OnboardingProgress(BaseModel):
    """User's onboarding progress"""
    user_id: int
    current_step: OnboardingStep
    completed_steps: List[OnboardingStep]
    skipped_steps: List[OnboardingStep]
    started_at: datetime
    completed_at: Optional[datetime] = None
    last_active: datetime
    completed_guides: List[str] = []  # Add this field


class GuideStep(BaseModel):
    """Individual step in a guide"""
    id: str
    title: str
    content: str
    target_element: Optional[str] = None  # CSS selector for element to highlight
    position: str="bottom"  # Position of the guide tooltip
    action_required: bool=False
    action_text: Optional[str] = None


class Guide(BaseModel):
    """In - app guide definition"""
    id: str
    name: str
    description: str
    type: GuideType
    steps: List[GuideStep]
    prerequisites: List[str] = []  # Other guide IDs that must be completed first
    auto_start: bool=False
    show_progress: bool=True


class OnboardingManager:
    """Manages user onboarding and guides"""


    def __init__(self):
        self.guides=self._initialize_guides()
        self.user_progress: Dict[int, OnboardingProgress] = {}


    def _initialize_guides(self) -> Dict[str, Guide]:
        """Initialize built - in guides"""
        guides={}

        # Main onboarding guide
        guides["main_onboarding"] = Guide(
            id="main_onboarding",
                name="Welcome to Klerno Labs",
                description="Get started with AML risk intelligence",
                type=GuideType.ONBOARDING,
                auto_start=True,
                steps=[
                GuideStep(
                    id="welcome",
                        title="Welcome to Klerno Labs!",
                        content="Welcome to the world's most advanced AML risk intelligence platform. Let's get you set up in just a few steps.",
                        target_element=".navbar - brand",
                        position="bottom"
                ),
                    GuideStep(
                    id="dashboard_overview",
                        title="Your Analytics Dashboard",
                        content="This is your main dashboard where you'll see real - time transaction analytics, risk scores, and alerts.",
                        target_element=".metrics - overview",
                        position="bottom"
                ),
                    GuideStep(
                    id="quick_actions",
                        title="Quick Actions",
                        content="Use these buttons to analyze sample data, fetch XRPL transactions, or export your results.",
                        target_element=".quick - actions",
                        position="top"
                ),
                    GuideStep(
                    id="load_sample",
                        title="Try Sample Data",
                        content="Click 'Load demo data' to see how Klerno Labs analyzes transactions and identifies risks.",
                        target_element="button:contains('Load demo data')",
                        position="top",
                        action_required=True,
                        action_text="Click to load sample data"
                ),
                    GuideStep(
                    id="view_results",
                        title="Review the Results",
                        content="Great! Now you can see how transactions are categorized and scored for risk. High - risk transactions appear in red.",
                        target_element=".recent - transactions",
                        position="top"
                )
            ]
        )

        # API setup guide
        guides["api_setup"] = Guide(
            id="api_setup",
                name="API Key Configuration",
                description="Learn how to set up and use API keys",
                type=GuideType.FEATURE_INTRO,
                steps=[
                GuideStep(
                    id="api_importance",
                        title="Why API Keys Matter",
                        content="API keys allow you to programmatically access Klerno Labs functionality and integrate with your existing systems.",
                        target_element=".nav - link[href*='admin']",
                        position="bottom"
                ),
                    GuideStep(
                    id="generate_key",
                        title="Generate Your API Key",
                        content="Go to the Admin tab to generate and manage your API keys. Keep them secure!",
                        target_element="tab[name='Admin']",
                        position="bottom",
                        action_required=True,
                        action_text="Click Admin tab"
                )
            ]
        )

        # Advanced features guide
        guides["advanced_features"] = Guide(
            id="advanced_features",
                name="Advanced Analytics Features",
                description="Discover powerful analytics and insights",
                type=GuideType.FEATURE_INTRO,
                prerequisites=["main_onboarding"],
                steps=[
                GuideStep(
                    id="explore_tab",
                        title="Explore Transactions",
                        content="Use the Explore tab to search and filter transactions with advanced criteria.",
                        target_element="tab[name='Explore']",
                        position="bottom"
                ),
                    GuideStep(
                    id="alerts_system",
                        title="Smart Alerts",
                        content="The Alerts tab shows high - risk transactions that need your attention, complete with AI explanations.",
                        target_element="tab[name='Alerts']",
                        position="bottom"
                ),
                    GuideStep(
                    id="profile_reports",
                        title="Compliance Reports",
                        content="Generate compliance reports and export data in formats suitable for regulatory filing.",
                        target_element="tab[name='Profile']",
                        position="bottom"
                )
            ]
        )

        return guides


    def get_user_progress(self, user_id: int) -> Optional[OnboardingProgress]:
        """Get onboarding progress for a user"""
        return self.user_progress.get(user_id)


    def start_onboarding(self, user_id: int) -> OnboardingProgress:
        """Start onboarding for a new user"""
        progress=OnboardingProgress(
            user_id=user_id,
                current_step=OnboardingStep.WELCOME,
                completed_steps=[],
                skipped_steps=[],
                started_at=datetime.utcnow(),
                last_active=datetime.utcnow()
        )
        self.user_progress[user_id] = progress
        return progress


    def advance_step(self, user_id: int, step: OnboardingStep, skipped: bool = False) -> OnboardingProgress:
        """Advance user to the next onboarding step"""
        progress=self.user_progress.get(user_id)
        if not progress:
            progress=self.start_onboarding(user_id)

        if skipped:
            progress.skipped_steps.append(step)
        else:
            progress.completed_steps.append(step)

        # Determine next step
        all_steps=list(OnboardingStep)
        current_index=all_steps.index(progress.current_step)

        if current_index < len(all_steps) - 1:
            progress.current_step=all_steps[current_index + 1]

        # Check if we've completed onboarding
        if progress.current_step == OnboardingStep.COMPLETED:
            progress.completed_at=datetime.utcnow()

        progress.last_active=datetime.utcnow()
        return progress


    def get_available_guides(self, user_id: int) -> List[Guide]:
        """Get guides available to a user based on their progress"""
        progress=self.user_progress.get(user_id)
        if not progress:
            return [guide for guide in self.guides.values() if guide.auto_start]

        available=[]
        completed_guide_ids=set(progress.completed_guides) if progress else set()

        for guide in self.guides.values():
            # Check if prerequisites are met
            if all(prereq in completed_guide_ids for prereq in guide.prerequisites):
                available.append(guide)

        return available


    def mark_guide_completed(self, user_id: int, guide_id: str):
        """Mark a guide as completed for a user"""
        progress=self.user_progress.get(user_id)
        if not progress:
            return

        progress.completed_guides.append(guide_id)
        progress.last_active=datetime.utcnow()


    def get_next_suggested_action(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get the next suggested action for a user"""
        progress=self.user_progress.get(user_id)
        if not progress:
            return {
                "action": "start_onboarding",
                    "title": "Get Started",
                    "description": "Welcome to Klerno Labs! Let's set up your account.",
                    "button_text": "Start Tour"
            }

        if progress.current_step == OnboardingStep.COMPLETED:
            return None

        step_actions={
            OnboardingStep.WELCOME: {
                "action": "dashboard_tour",
                    "title": "Take the Dashboard Tour",
                    "description": "Learn how to navigate your analytics dashboard.",
                    "button_text": "Start Tour"
            },
                OnboardingStep.API_KEY_SETUP: {
                "action": "setup_api_key",
                    "title": "Set Up API Access",
                    "description": "Generate your API key to enable programmatic access.",
                    "button_text": "Generate API Key"
            },
                OnboardingStep.FIRST_TRANSACTION: {
                "action": "analyze_sample",
                    "title": "Analyze Sample Data",
                    "description": "See how Klerno Labs identifies risks in transactions.",
                    "button_text": "Load Sample Data"
            },
                OnboardingStep.DASHBOARD_TOUR: {
                "action": "explore_features",
                    "title": "Explore Advanced Features",
                    "description": "Discover alerts, reporting, and advanced analytics.",
                    "button_text": "Explore Features"
            }
        }

        return step_actions.get(progress.current_step)


# Quick tips and contextual help


class ContextualHelp:
    """Provides contextual help and tips throughout the application"""


    def __init__(self):
        self.tips=self._initialize_tips()


    def _initialize_tips(self) -> Dict[str, Dict[str, Any]]:
        """Initialize contextual help tips"""
        return {
            "dashboard": {
                "title": "Dashboard Overview",
                    "tips": [
                    "Risk scores range from 0 (low risk) to 1 (high risk)",
                        "Red transactions require immediate attention",
                        "Use filters to focus on specific time periods or risk levels",
                        "Export data for compliance reporting and audits"
                ]
            },
                "alerts": {
                "title": "Understanding Alerts",
                    "tips": [
                    "Alerts are triggered when transactions exceed your risk threshold",
                        "Each alert includes an AI explanation of why it was flagged",
                        "Click on any alert to see detailed analysis",
                        "Adjust thresholds in Settings to reduce false positives"
                ]
            },
                "api": {
                "title": "API Usage",
                    "tips": [
                    "Use API keys for programmatic access to Klerno Labs",
                        "Rate limits apply to protect system performance",
                        "Always validate transaction data before analysis",
                        "Batch analysis is more efficient for large datasets"
                ]
            },
                "compliance": {
                "title": "Compliance Best Practices",
                    "tips": [
                    "Regularly export transaction data for regulatory filing",
                        "Set up automated alerts for suspicious activities",
                        "Review high - risk transactions within 24 hours",
                        "Document all investigation actions and decisions"
                ]
            }
        }


    def get_tips_for_section(self, section: str) -> Optional[Dict[str, Any]]:
        """Get contextual tips for a specific section"""
        return self.tips.get(section)


    def get_quick_tip(self, user_experience_level: str = "beginner") -> Dict[str, str]:
        """Get a quick tip based on user experience level"""
        tips_by_level={
            "beginner": [
                "Start by loading sample data to see how the system works",
                    "Red numbers indicate high - risk transactions that need attention",
                    "Use the Export CSV feature to save your analysis results",
                    "Check the Alerts tab daily for new high - risk transactions"
            ],
                "intermediate": [
                "Set up custom risk thresholds based on your compliance requirements",
                    "Use the API to integrate Klerno Labs with your existing systems",
                    "Review hourly activity patterns to identify unusual behavior",
                    "Export reports in different formats for various stakeholders"
            ],
                "advanced": [
                "Leverage the plugin system to extend functionality",
                    "Use batch analysis for processing large transaction volumes",
                    "Monitor network analysis metrics for money laundering patterns",
                    "Set up automated workflows using webhooks and API integration"
            ]
        }

        tips=tips_by_level.get(user_experience_level, tips_by_level["beginner"])
        import random
        selected_tip=random.choice(tips)

        # Use the actual level that has tips, not the requested level
        actual_level=user_experience_level if user_experience_level in tips_by_level else "beginner"

        return {
            "tip": selected_tip,
                "level": actual_level,
                "category": "quick_tip"
        }


# Global instances
onboarding_manager=OnboardingManager()
contextual_help=ContextualHelp()
