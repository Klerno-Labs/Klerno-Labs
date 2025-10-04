"""Tests for onboarding and user experience features"""

import pytest

from app.onboarding import ContextualHelp, GuideType, OnboardingManager, OnboardingStep


def test_onboarding_manager_initialization():
    """Test OnboardingManager initialization"""
    manager = OnboardingManager()

    # Should have built - in guides
    assert len(manager.guides) > 0
    assert "main_onboarding" in manager.guides
    assert "api_setup" in manager.guides

    # Should have empty user progress
    assert len(manager.user_progress) == 0


def test_start_onboarding():
    """Test starting onboarding for a new user"""
    manager = OnboardingManager()

    user_id = 123
    progress = manager.start_onboarding(user_id)

    assert progress.user_id == user_id
    assert progress.current_step == OnboardingStep.WELCOME
    assert len(progress.completed_steps) == 0
    assert len(progress.skipped_steps) == 0
    assert progress.completed_at is None

    # Should be stored in manager
    assert user_id in manager.user_progress


def test_advance_onboarding_step():
    """Test advancing through onboarding steps"""
    manager = OnboardingManager()

    user_id = 123
    manager.start_onboarding(user_id)

    # Advance from welcome step
    progress = manager.advance_step(user_id, OnboardingStep.WELCOME)

    assert OnboardingStep.WELCOME in progress.completed_steps
    assert progress.current_step == OnboardingStep.API_KEY_SETUP

    # Skip a step
    progress = manager.advance_step(user_id, OnboardingStep.API_KEY_SETUP, skipped=True)

    assert OnboardingStep.API_KEY_SETUP in progress.skipped_steps
    assert OnboardingStep.API_KEY_SETUP not in progress.completed_steps
    assert progress.current_step == OnboardingStep.FIRST_TRANSACTION


def test_onboarding_completion():
    """Test completing onboarding"""
    manager = OnboardingManager()

    user_id = 123
    manager.start_onboarding(user_id)

    # Advance through all steps
    steps = list(OnboardingStep)
    for _i, step in enumerate(steps[:-1]):  # Exclude COMPLETED
        manager.advance_step(user_id, step)

    progress = manager.user_progress[user_id]
    assert progress.current_step == OnboardingStep.COMPLETED
    assert progress.completed_at is not None


def test_get_next_suggested_action():
    """Test getting next suggested action"""
    manager = OnboardingManager()

    user_id = 123

    # New user should get start onboarding action
    action = manager.get_next_suggested_action(user_id)
    assert isinstance(action, dict)
    assert action.get("action") == "start_onboarding"

    # Start onboarding
    manager.start_onboarding(user_id)
    action = manager.get_next_suggested_action(user_id)
    assert isinstance(action, dict)
    assert action.get("action") == "dashboard_tour"

    # Advance to API setup
    manager.advance_step(user_id, OnboardingStep.WELCOME)
    action = manager.get_next_suggested_action(user_id)
    assert isinstance(action, dict)
    assert action.get("action") == "setup_api_key"


def test_available_guides():
    """Test getting available guides for user"""
    manager = OnboardingManager()

    user_id = 123

    # New user should get auto - start guides
    guides = manager.get_available_guides(user_id)
    auto_start_guides = [g for g in guides if g.auto_start]
    assert len(auto_start_guides) > 0

    # Start onboarding
    manager.start_onboarding(user_id)

    # Should get all guides (simplified test - no complex prerequisites)
    guides = manager.get_available_guides(user_id)
    assert len(guides) > 0


def test_contextual_help():
    """Test contextual help system"""
    help_system = ContextualHelp()

    # Test getting tips for a section
    dashboard_tips = help_system.get_tips_for_section("dashboard")
    assert dashboard_tips is not None
    assert "title" in dashboard_tips
    assert "tips" in dashboard_tips
    assert len(dashboard_tips["tips"]) > 0

    # Test non - existent section
    missing_tips = help_system.get_tips_for_section("nonexistent")
    assert missing_tips is None


def test_quick_tips():
    """Test quick tip generation"""
    help_system = ContextualHelp()

    # Test beginner tip
    beginner_tip = help_system.get_quick_tip("beginner")
    assert "tip" in beginner_tip
    assert beginner_tip["level"] == "beginner"
    assert beginner_tip["category"] == "quick_tip"

    # Test advanced tip
    advanced_tip = help_system.get_quick_tip("advanced")
    assert "tip" in advanced_tip
    assert advanced_tip["level"] == "advanced"

    # Test default level
    default_tip = help_system.get_quick_tip("unknown_level")
    assert default_tip["level"] == "beginner"  # Should default to beginner


def test_guide_structure():
    """Test guide data structure"""
    manager = OnboardingManager()

    main_guide = manager.guides["main_onboarding"]
    assert main_guide.id == "main_onboarding"
    assert main_guide.type == GuideType.ONBOARDING
    assert main_guide.auto_start is True
    assert len(main_guide.steps) > 0

    # Check step structure
    first_step = main_guide.steps[0]
    assert hasattr(first_step, "id")
    assert hasattr(first_step, "title")
    assert hasattr(first_step, "content")
    assert hasattr(first_step, "target_element")


def test_mark_guide_completed():
    """Test marking guides as completed"""
    manager = OnboardingManager()

    user_id = 123
    manager.start_onboarding(user_id)

    # Mark guide as completed
    guide_id = "main_onboarding"
    manager.mark_guide_completed(user_id, guide_id)

    progress = manager.user_progress[user_id]
    assert hasattr(progress, "completed_guides")
    assert guide_id in progress.completed_guides


if __name__ == "__main__":
    pytest.main([__file__])
