import pytest

from researchdesk.scope import capability_gap


@pytest.mark.parametrize(
    "question",
    [
        "What was Contoso's revenue in 2024?",
        "How did Alpine Widgets revenue change?",
        "What was the closing share price?",
        "What are confidential component prices?",
        "What is the guaranteed revenue next year?",
        "Does the report disclose next year's exact revenue?",
        "How many devices were sold each month?",
        "What is the chief executive's favorite breakfast?",
    ],
)
def test_unsupported_capabilities_fail_closed(question):
    assert capability_gap(question, "AAPL")


@pytest.mark.parametrize(
    "question",
    [
        "How did revenue and operating margin change between 2023 and 2024?",
        "What was Apple's consolidated annual revenue in fiscal 2023? State USD millions.",
        "Which supply-chain risks does Apple disclose in 2024?",
        "What personal information risks are disclosed?",
        "Did fiscal 2023 have 53 weeks?",
        "How can acquisition financing restrict flexibility?",
        "What does the 2024 evidence say about Apple's revenue when the supplied evidence conflicts?",
        "What is the risk to Apple's supply chain?",
        "What does the evidence say about the company's revenue?",
    ],
)
def test_supported_scope_remains_available(question):
    assert capability_gap(question, "AAPL") is None


@pytest.mark.parametrize(
    "question",
    [
        "Explain how trade restrictions affect costs in FY2024",
        "Describe inventory practices and customization in FY2023",
        "Why are third-party software developers important in 2024?",
        "Describe the consequences of tariffs in 2023",
    ],
)
def test_documentary_business_mechanisms_are_not_blocked_by_topic_keywords(question):
    assert capability_gap(question, "AAPL") is None
