from packages.surveillance.data.database import (
    create_database_engine,
    create_session_factory,
    initialize_schema,
)
from packages.surveillance.data.repositories import SqlAlchemyThresholdProfileRepository
from packages.surveillance.domain.models import LearnedThresholdProfile


def test_learned_threshold_profile_persists_by_tenant_and_location() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    initialize_schema(engine)
    repository = SqlAlchemyThresholdProfileRepository(create_session_factory(engine))
    profile = LearnedThresholdProfile(
        organization_id="org-1",
        location="North Gate",
        threshold=0.6612,
        applied_review_versions=("incident-1@2026-09-27T10:00:00+00:00",),
    )

    repository.save(profile)

    restored = repository.get("org-1", "  north   gate ")
    assert restored is not None
    assert restored.threshold == 0.6612
    assert restored.applied_review_versions == profile.applied_review_versions
    assert repository.get("org-2", "North Gate") is None
