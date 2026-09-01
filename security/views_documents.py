from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views import View

from security.audit import log_event
from security.documents import EncryptedFileService
from security.models import EncryptedDocument


class DocumentListView(View):
    def get(self, request):
        svc = EncryptedFileService()
        docs = []
        for doc in EncryptedDocument.objects.order_by("-created_at"):
            try:
                name = svc.read_filename(doc)
            except Exception:
                name = "(indisponível)"
            docs.append({"id": doc.pk, "name": name})
        return render(request, "security/documents.html", {"documents": docs})

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return redirect("documents")
        EncryptedFileService().store(upload.name, upload.read())
        log_event("DOCUMENT_IMPORTED", resource_type="document")
        return redirect("documents")


class DocumentDownloadView(View):
    def get(self, request, pk):
        doc = EncryptedDocument.objects.filter(pk=pk).first()
        if doc is None:
            return redirect("documents")
        svc = EncryptedFileService()
        try:
            content = svc.read(doc)
            name = svc.read_filename(doc)
        except Exception:
            return render(request, "security/erro_download.html",
                          {"message": "Documento corrompido ou chave inválida."}, status=200)
        resp = HttpResponse(content, content_type="application/octet-stream")
        resp["Content-Disposition"] = f'attachment; filename="{name}"'
        log_event("DOCUMENT_EXPORTED", resource_type="document", resource_id=str(doc.pk))
        return resp