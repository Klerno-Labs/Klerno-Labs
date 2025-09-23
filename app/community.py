"""
Community and Collaboration Features for Klerno Labs
Provides forums, knowledge sharing, and collaborative features
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class PostType(str, Enum):
    """Types of community posts"""

    QUESTION = "question"
    DISCUSSION = "discussion"
    TUTORIAL = "tutorial"
    NEWS = "news"
    SHOWCASE = "showcase"


class PostStatus(str, Enum):
    """Status of community posts"""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    FLAGGED = "flagged"


class VoteType(str, Enum):
    """Vote types"""

    UPVOTE = "upvote"
    DOWNVOTE = "downvote"


class CommunityPost(BaseModel):
    """Community forum post"""

    id: int
    title: str
    content: str
    post_type: PostType
    status: PostStatus
    author_id: int
    author_name: str
    created_at: datetime
    updated_at: datetime
    upvotes: int = 0
    downvotes: int = 0
    view_count: int = 0
    reply_count: int = 0
    tags: list[str] = []
    is_pinned: bool = False
    is_solved: bool = False


class CommunityReply(BaseModel):
    """Reply to a community post"""

    id: int
    post_id: int
    content: str
    author_id: int
    author_name: str
    created_at: datetime
    updated_at: datetime
    upvotes: int = 0
    downvotes: int = 0
    is_solution: bool = False
    parent_reply_id: int | None = None


class KnowledgeArticle(BaseModel):
    """Knowledge base article"""

    id: int
    title: str
    content: str
    summary: str
    category: str
    tags: list[str]
    author_id: int
    author_name: str
    created_at: datetime
    updated_at: datetime
    view_count: int = 0
    helpful_votes: int = 0
    is_featured: bool = False
    difficulty_level: str = "beginner"  # beginner, intermediate, advanced


class TutorialStep(BaseModel):
    """Step in a tutorial"""

    step_number: int
    title: str
    content: str
    code_example: str | None = None
    image_url: str | None = None


class Tutorial(BaseModel):
    """Interactive tutorial"""

    id: int
    title: str
    description: str
    category: str
    difficulty_level: str
    estimated_time: int  # minutes
    author_id: int
    author_name: str
    steps: list[TutorialStep]
    created_at: datetime
    updated_at: datetime
    completion_count: int = 0
    rating: float = 0.0
    rating_count: int = 0


class UserContribution(BaseModel):
    """User's community contributions"""

    user_id: int
    posts_count: int
    replies_count: int
    upvotes_received: int
    helpful_votes: int
    tutorials_created: int
    reputation_score: int
    badges: list[str] = []
    join_date: datetime
    last_active: datetime


class CommunityManager:
    """Manages community features and interactions"""

    def __init__(self):
        self.posts: dict[int, CommunityPost] = {}
        self.replies: dict[int, list[CommunityReply]] = {}
        self.knowledge_articles: dict[int, KnowledgeArticle] = {}
        self.tutorials: dict[int, Tutorial] = {}
        self.user_contributions: dict[int, UserContribution] = {}
        self.votes: dict[str, dict[int, VoteType]] = (
            {}
        )  # user_id -> {post_id: vote_type}

        # Initialize with sample content
        self._initialize_sample_content()

    def _initialize_sample_content(self):
        """Initialize with sample community content"""

        # Sample knowledge articles
        self.knowledge_articles[1] = KnowledgeArticle(
            id=1,
            title="Understanding Risk Scores in AML Analysis",
            content="""  # Understanding Risk Scores in AML Analysis

Risk scores in Klerno Labs range from 0.0 (low risk) to 1.0 (high risk). Here's how to interpret them:

## Risk Score Ranges

- **0.0 - 0.33**: Low Risk (Green)
  - Normal transaction patterns
  - Known addresses with good reputation
  - Typical amounts for the address / time period

- **0.34 - 0.66**: Medium Risk (Yellow)
  - Some unusual patterns detected
  - New addresses or infrequent activity
  - Amounts slightly above normal ranges

- **0.67 - 1.0**: High Risk (Red)
  - Multiple suspicious indicators
  - Potential money laundering patterns
  - Very large amounts or unusual timing
  - Known high - risk addresses involved

## What Influences Risk Scores

1. **Transaction Amount**: Unusually large amounts increase risk
2. **Address Reputation**: Known addresses affect scoring
3. **Timing Patterns**: Transactions at unusual times
4. **Network Analysis**: Position in transaction graphs
5. **Historical Behavior**: Deviation from normal patterns

## Best Practices

- Set thresholds based on your risk tolerance
- Review all high - risk transactions manually
- Use the AI explanations to understand why transactions were flagged
- Adjust thresholds based on false positive rates
""",
            summary="Learn how risk scores work and how to interpret them for effective AML compliance",
            category="Risk Analysis",
            tags=["risk - scores", "aml", "compliance", "basics"],
            author_id=1,
            author_name="Klerno Team",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            view_count=245,
            helpful_votes=89,
            is_featured=True,
            difficulty_level="beginner",
        )

        self.knowledge_articles[2] = KnowledgeArticle(
            id=2,
            title="Advanced API Integration Patterns",
            content="""  # Advanced API Integration Patterns

## Batch Processing Best Practices

When processing large volumes of transactions, use these patterns:

### 1. Optimal Batch Sizes
```python
# Process in batches of 100 - 500 transactions
batch_size=250
for i in range(0, len(transactions), batch_size):
    batch=transactions[i:i + batch_size]
    result=client.analyze_batch(batch)
    process_results(result)
```

### 2. Rate Limit Handling
```python
import time
from requests.exceptions import HTTPError


def analyze_with_retry(client, transaction):
    max_retries=3
    for attempt in range(max_retries):
        try:
            return client.analyze_transaction(transaction)
        except HTTPError as e:
            if e.response.status_code == 429:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
    raise Exception("Max retries exceeded")
```

### 3. Webhook Processing
```python
from flask import Flask, request
import hmac
import hashlib

app=Flask(__name__)

@app.route('/klerno - webhook', methods=['POST'])


def handle_webhook():
    signature=request.headers.get('X-Klerno-Signature')
    payload=request.get_data()

    # Verify signature
    if not verify_signature(payload, signature):
        return 'Unauthorized', 401

    data=request.get_json()
    if data['event'] == 'alert_generated':
        process_alert(data['data'])

    return 'OK', 200
```

## Error Handling Strategies

Always implement comprehensive error handling:

```python


class KlernoAPIError(Exception):
    pass


def safe_analyze(client, transaction):
    try:
        result=client.analyze_transaction(transaction)
        return result
    except HTTPError as e:
        if e.response.status_code == 400:
            logger.error(f"Invalid transaction data: {e.response.text}")
        elif e.response.status_code == 401:
            logger.error("Invalid API key")
        elif e.response.status_code == 429:
            logger.warning("Rate limited - implement backoff")
        else:
            logger.error(f"API error {e.response.status_code}: {e.response.text}")
        raise KlernoAPIError(f"API call failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
```
""",
            summary="Advanced patterns for integrating with the Klerno Labs API at scale",
            category="API Integration",
            tags=["api", "integration", "batch - processing", "webhooks", "advanced"],
            author_id=1,
            author_name="Klerno Team",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            view_count=156,
            helpful_votes=72,
            is_featured=True,
            difficulty_level="advanced",
        )

        # Sample community posts
        self.posts[1] = CommunityPost(
            id=1,
            title="Best practices for setting risk thresholds?",
            content=(
                """I'm new to AML compliance and trying to figure out the optimal risk threshold "
                "settings for our organization. We're a mid - size fintech company processing "
                "about 10K transactions per day.\n\nCurrently, we have the threshold set at "
                "0.75, but we're getting too many false positives. Should we increase it to "
                "0.85 or 0.9? What do other organizations typically use?\n\nAlso, should "
                "thresholds vary by transaction amount or time of day?"""
            ),
            post_type=PostType.QUESTION,
            status=PostStatus.PUBLISHED,
            author_id=2,
            author_name="ComplianceOfficer_Mike",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            upvotes=15,
            downvotes=0,
            view_count=89,
            reply_count=7,
            tags=["risk - thresholds", "compliance", "best - practices"],
            is_solved=True,
        )

        # Sample replies
        self.replies[1] = [
            CommunityReply(
                id=1,
                post_id=1,
                content=(
                    """Great question! In our experience, 0.75 is actually quite conservative. "
                    "Here's what we've learned:\n\n1. **Start with 0.85** for most organizations - "
                    "this significantly reduces false positives while still catching genuine "
                    "risks\n2. **Use dynamic thresholds** based on transaction amount:\n   - "
                    "Amounts < $1, 000: 0.9 threshold\n   - $1, 000 - $10, 000: 0.85 "
                    "threshold\n   - $10, 000+: 0.75 threshold\n3. **Time - based adjustments** "
                    "can help - slightly lower thresholds during off - hours when legitimate "
                    "activity is lower\n\nThe key is to monitor your false positive rate and adjust accordingly. "
                    "Aim for < 5% false positives for best efficiency."""
                ),
                author_id=3,
                author_name="AML_Expert_Sarah",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                upvotes=23,
                downvotes=1,
                is_solution=True,
            ),
            CommunityReply(
                id=2,
                post_id=1,
                content="""We use a tiered approach based on customer risk profiles:

- **Low - risk customers**: 0.9 threshold
- **Medium - risk customers**: 0.8 threshold
- **High - risk customers**: 0.7 threshold

This has worked well for us and reduces alert fatigue significantly.""",
                author_id=4,
                author_name="RegTech_Dev",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                upvotes=12,
                downvotes=0,
            ),
        ]

    def get_featured_content(self) -> dict[str, list[Any]]:
        """Get featured community content for the homepage"""
        featured_articles = [
            article
            for article in self.knowledge_articles.values()
            if article.is_featured
        ]

        popular_posts = sorted(
            [
                post
                for post in self.posts.values()
                if post.status == PostStatus.PUBLISHED
            ],
            key=lambda p: p.upvotes + p.view_count,
            reverse=True,
        )[:5]

        return {"featured_articles": featured_articles, "popular_posts": popular_posts}

    def search_content(self, query: str, content_type: str = "all") -> list[Any]:
        """Search community content"""
        results = []
        query_lower = query.lower()

        if content_type in ["all", "articles"]:
            for article in self.knowledge_articles.values():
                if (
                    query_lower in article.title.lower()
                    or query_lower in article.content.lower()
                    or any(query_lower in tag for tag in article.tags)
                ):
                    results.append({"type": "article", "item": article})

        if content_type in ["all", "posts"]:
            for post in self.posts.values():
                if post.status == PostStatus.PUBLISHED and (
                    query_lower in post.title.lower()
                    or query_lower in post.content.lower()
                    or any(query_lower in tag for tag in post.tags)
                ):
                    results.append({"type": "post", "item": post})

        return results

    def get_user_contributions(self, user_id: int) -> UserContribution | None:
        """Get user's community contributions and reputation"""
        return self.user_contributions.get(user_id)

    def create_post(
        self,
        title: str,
        content: str,
        post_type: PostType,
        author_id: int,
        author_name: str,
        tags: list[str] | None = None,
    ) -> CommunityPost:
        """Create a new community post"""
        post_id = max(self.posts, default=0) + 1

        post = CommunityPost(
            id=post_id,
            title=title,
            content=content,
            post_type=post_type,
            status=PostStatus.PUBLISHED,
            author_id=author_id,
            author_name=author_name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tags=tags or [],
        )

        self.posts[post_id] = post
        return post

    def add_reply(
        self,
        post_id: int,
        content: str,
        author_id: int,
        author_name: str,
        parent_reply_id: int | None = None,
    ) -> CommunityReply:
        """Add a reply to a post"""
        if post_id not in self.posts:
            raise ValueError("Post not found")

        reply_id = (
            max([r.id for replies in self.replies.values() for r in replies], default=0)
            + 1
        )

        reply = CommunityReply(
            id=reply_id,
            post_id=post_id,
            content=content,
            author_id=author_id,
            author_name=author_name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            parent_reply_id=parent_reply_id,
        )

        if post_id not in self.replies:
            self.replies[post_id] = []
        self.replies[post_id].append(reply)

        # Update post reply count
        self.posts[post_id].reply_count += 1

        return reply

    def vote_on_post(self, user_id: int, post_id: int, vote_type: VoteType):
        """Vote on a post"""
        if post_id not in self.posts:
            raise ValueError("Post not found")

        user_votes = self.votes.setdefault(str(user_id), {})
        previous_vote = user_votes.get(post_id)

        # Remove previous vote if exists
        if previous_vote:
            if previous_vote == VoteType.UPVOTE:
                self.posts[post_id].upvotes -= 1
            else:
                self.posts[post_id].downvotes -= 1

        # Add new vote if different from previous
        if previous_vote != vote_type:
            user_votes[post_id] = vote_type
            if vote_type == VoteType.UPVOTE:
                self.posts[post_id].upvotes += 1
            else:
                self.posts[post_id].downvotes += 1
        else:
            # Remove vote if same as previous
            del user_votes[post_id]

    def get_trending_topics(self) -> list[dict[str, Any]]:
        """Get trending topics and tags"""
        tag_counts: dict[str, int] = {}

        # Count tags from recent posts (last 30 days)
        cutoff = datetime.utcnow().timestamp() - (30 * 24 * 60 * 60)

        for post in self.posts.values():
            if post.created_at.timestamp() > cutoff:
                for tag in post.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by count and engagement
        trending = []
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
            trending.append(
                {
                    "tag": tag,
                    "post_count": count,
                    "growth": "up",  # Simplified - would calculate actual growth
                }
            )

        return trending[:10]


class CollaborationFeatures:
    """Features for team collaboration and knowledge sharing"""

    def __init__(self):
        self.shared_workspaces: dict[int, dict[str, Any]] = {}
        self.team_annotations: dict[str, list[dict[str, Any]]] = {}

    def create_shared_workspace(
        self, name: str, description: str, owner_id: int, team_members: list[int]
    ) -> dict[str, Any]:
        """Create a shared workspace for team collaboration"""
        workspace_id = max(self.shared_workspaces, default=0) + 1

        workspace = {
            "id": workspace_id,
            "name": name,
            "description": description,
            "owner_id": owner_id,
            "members": team_members,
            "created_at": datetime.utcnow(),
            "shared_queries": [],
            "shared_reports": [],
            "annotations": [],
        }

        self.shared_workspaces[workspace_id] = workspace
        return workspace

    def add_annotation(
        self,
        transaction_id: str,
        user_id: int,
        annotation: str,
        annotation_type: str = "note",
    ) -> dict[str, Any]:
        """Add annotation to a transaction for team collaboration"""
        if transaction_id not in self.team_annotations:
            self.team_annotations[transaction_id] = []

        annotation_obj = {
            "id": len(self.team_annotations[transaction_id]) + 1,
            "user_id": user_id,
            "annotation": annotation,
            "type": annotation_type,  # note, flag, question, resolved
            "created_at": datetime.utcnow(),
            "is_resolved": False,
        }

        self.team_annotations[transaction_id].append(annotation_obj)
        return annotation_obj

    def get_team_insights(self, workspace_id: int) -> dict[str, Any]:
        """Get collaborative insights for a team workspace"""
        if workspace_id not in self.shared_workspaces:
            return {}

        workspace = self.shared_workspaces[workspace_id]

        return {
            "workspace": workspace,
            "recent_activity": [
                {"action": "annotation_added", "user": "Sarah", "time": "2 hours ago"},
                {"action": "query_shared", "user": "Mike", "time": "4 hours ago"},
                {"action": "report_generated", "user": "Alex", "time": "1 day ago"},
            ],
            "team_stats": {
                "total_annotations": sum(
                    len(annotations) for annotations in self.team_annotations.values()
                ),
                "resolved_issues": 45,
                "shared_queries": len(workspace["shared_queries"]),
                "active_members": len(workspace["members"]),
            },
        }


# Global instances
community_manager = CommunityManager()
collaboration_features = CollaborationFeatures()
