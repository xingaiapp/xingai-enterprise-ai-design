from re import findall

from .auth import AuthorizationRequest, PolicyEngine
from .models import Document, Evidence, RequestContext


def _tokens(text: str) -> set[str]:
    return set(findall(r"[a-z0-9]+", text.lower()))


class AuthorizedRetriever:
    """ACL-first lexical baseline; replace ranking adapter without changing policy."""

    def __init__(self, documents: list[Document], policy: PolicyEngine) -> None:
        self.documents = documents
        self.policy = policy

    def retrieve(self, query: str, context: RequestContext, limit: int = 5) -> tuple[Evidence, ...]:
        context.assert_active()
        query_tokens = _tokens(query)
        ranked: list[Evidence] = []
        for document in self.documents:
            try:
                self.policy.authorize(
                    AuthorizationRequest(
                        actor=context.actor,
                        action="document.read",
                        resource_tenant_id=document.tenant_id,
                        required_scope="knowledge:read",
                        allowed_roles=document.allowed_roles,
                    )
                )
            except PermissionError:
                continue
            document_tokens = _tokens(document.text)
            score = len(query_tokens & document_tokens) / max(len(query_tokens), 1)
            if score:
                ranked.append(Evidence(document.document_id, document.text[:240], score, document.version))
        return tuple(sorted(ranked, key=lambda item: item.score, reverse=True)[:limit])

