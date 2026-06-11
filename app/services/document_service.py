# app/services/document_service.py

import os
import io
from uuid import UUID, uuid4
from datetime import datetime, timezone, date
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.client import Client
from app.repositories.document_repository import DocumentRepository
from app.repositories.client_repository import ClientRepository
from app.services.audit_service import AuditService


# Шаблоны документов
DOCUMENT_TEMPLATES = {
    "contract_standard": {
        "name": "Договор оказания услуг (стандартный)",
        "type": "contract",
        "filename_prefix": "dogovor_uslug",
    },
    "contract_vip": {
        "name": "Договор VIP",
        "type": "contract",
        "filename_prefix": "dogovor_vip",
    },
    "consent_personal": {
        "name": "Согласие на обработку персональных данных",
        "type": "consent",
        "filename_prefix": "soglasie_pdn",
    },
    "medical_clearance": {
        "name": "Медицинская справка",
        "type": "medical",
        "filename_prefix": "med_spravka",
    },
    "cancel_request": {
        "name": "Заявление на расторжение договора",
        "type": "request",
        "filename_prefix": "zayavlenie_rastorzhenie",
    },
    "receipt": {
        "name": "Квитанция об оплате",
        "type": "receipt",
        "filename_prefix": "kvitanciya",
    },
}


class DocumentService:
    """Сервис управления документами — генерация PDF, хранение, выдача"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DocumentRepository(db)
        self.client_repo = ClientRepository(db)
        self.audit = AuditService(db)

    # ============================================================
    # ШАБЛОНЫ
    # ============================================================

    def list_templates(self) -> list[dict]:
        """Список доступных шаблонов документов"""
        return [
            {"id": tid, "name": t["name"], "type": t["type"]}
            for tid, t in DOCUMENT_TEMPLATES.items()
        ]

    def get_template(self, template_id: str) -> dict:
        """Получить информацию о шаблоне"""
        if template_id not in DOCUMENT_TEMPLATES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Шаблон '{template_id}' не найден"
            )
        t = DOCUMENT_TEMPLATES[template_id]
        return {"id": template_id, "name": t["name"], "type": t["type"]}

    # ============================================================
    # CRUD ДОКУМЕНТОВ
    # ============================================================

    def list_client_documents(
        self,
        client_id: UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> dict:
        """Документы клиента"""
        client = self.client_repo.get_by_id(str(client_id))
        if not client:
            raise HTTPException(status_code=404, detail="Клиент не найден")

        docs, total = self.repo.list_by_client(client_id, offset, limit)
        return {
            "client_id": str(client_id),
            "client_name": f"{client.first_name} {client.last_name}",
            "items": [self._serialize_doc(d) for d in docs],
            "total": total,
        }

    def list_all_documents(
        self,
        offset: int = 0,
        limit: int = 100,
        doc_type: str | None = None,
        status: str | None = None,
    ) -> dict:
        """Все документы"""
        docs, total = self.repo.list_all(offset, limit, doc_type, status)
        return {
            "items": [self._serialize_doc(d) for d in docs],
            "total": total,
        }

    def get_document(self, doc_id: UUID) -> Document:
        """Получить документ по ID"""
        doc = self.repo.get_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Документ не найден")
        return doc

    # ============================================================
    # ГЕНЕРАЦИЯ PDF
    # ============================================================

    def generate_pdf(
        self,
        template_id: str,
        client_id: UUID,
        actor_user_id: UUID | None = None,
        extra_data: dict | None = None,
    ) -> dict:
        """
        Сгенерировать PDF документ из шаблона.
        Возвращает метаданные документа (PDF сохраняется в БД как blob).
        """
        template = self.get_template(template_id)
        client = self.client_repo.get_by_id(str(client_id))
        if not client:
            raise HTTPException(status_code=404, detail="Клиент не найден")

        # Генерируем PDF в памяти
        pdf_bytes = self._render_pdf(template_id, client, extra_data or {})

        # Создаём запись в БД
        doc = Document(
            id=uuid4(),
            client_id=client_id,
            doc_type=template["type"],
            template_id=template_id,
            title=template["name"],
            filename=self._make_filename(template_id, client),
            content_type="application/pdf",
            file_size=len(pdf_bytes),
            pdf_data=pdf_bytes,
            status="generated",
            generated_by=actor_user_id,
            extra_data={
                "template": template_id,
                "client_name": f"{client.first_name} {client.last_name}",
                **(extra_data or {}),
            },
        )

        self.repo.create(doc)

        self.audit.log(
            action="document.generate",
            status="success",
            actor_user_id=actor_user_id,
            target_client_id=client_id,
            message=f"Сгенерирован документ '{template['name']}' для {client.first_name} {client.last_name}",
            after_data={"document_id": str(doc.id), "template": template_id},
        )

        return self._serialize_doc(doc)

    def download_pdf(self, doc_id: UUID) -> StreamingResponse:
        """Скачать PDF документ"""
        doc = self.get_document(doc_id)

        if not doc.pdf_data:
            raise HTTPException(status_code=404, detail="PDF не найден")

        return StreamingResponse(
            io.BytesIO(doc.pdf_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{doc.filename}"',
                "Content-Length": str(len(doc.pdf_data)),
            },
        )

    def preview_pdf(self, doc_id: UUID) -> StreamingResponse:
        """Просмотр PDF (inline)"""
        doc = self.get_document(doc_id)

        if not doc.pdf_data:
            raise HTTPException(status_code=404, detail="PDF не найден")

        return StreamingResponse(
            io.BytesIO(doc.pdf_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{doc.filename}"',
            },
        )

    def sign_document(
        self,
        doc_id: UUID,
        actor_user_id: UUID | None = None,
    ) -> dict:
        """Подписать документ (электронно)"""
        doc = self.get_document(doc_id)

        if doc.status == "signed":
            raise HTTPException(status_code=400, detail="Документ уже подписан")

        doc.status = "signed"
        doc.signed_at = datetime.now(timezone.utc)
        self.repo.update(doc)

        self.audit.log(
            action="document.sign",
            status="success",
            actor_user_id=actor_user_id,
            target_client_id=doc.client_id,
            message=f"Документ '{doc.title}' подписан",
            after_data={"signed_at": doc.signed_at.isoformat()},
        )

        return self._serialize_doc(doc)

    # ============================================================
    # PDF РЕНДЕРИНГ (ReportLab)
    # ============================================================

    def _render_pdf(self, template_id: str, client: Client, extra: dict) -> bytes:
        """Сгенерировать PDF через ReportLab"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm, cm
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                HRFlowable, PageBreak
            )
            from reportlab.lib import colors
        except ImportError:
            # Fallback: генерируем минимальный PDF
            return self._render_minimal_pdf(template_id, client, extra)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        style_title = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        style_body = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
        )
        style_section = ParagraphStyle(
            'Section',
            parent=styles['Heading2'],
            fontSize=13,
            spaceAfter=10,
            spaceBefore=15,
        )

        story = []
        today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
        client_fio = f"{client.last_name} {client.first_name}"
        if client.middle_name:
            client_fio += f" {client.middle_name}"

        # === ЗАГОЛОВОК ===
        template_info = DOCUMENT_TEMPLATES.get(template_id, {})
        story.append(Paragraph(template_info.get("name", "Документ"), style_title))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 15))

        # === РЕЕСТР ===
        story.append(Paragraph("1. РЕКВИЗИТЫ ДОГОВОРА", style_section))
        data = [
            ["Дата составления:", today],
            ["Номер договора:", f"FIT-{datetime.now().strftime('%Y%m%d')}-{client.id.hex[:8].upper()}"],
            ["Место составления:", extra.get("city", "г. Москва")],
        ]
        t = Table(data, colWidths=[6 * cm, 10 * cm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#555555')),
        ]))
        story.append(t)
        story.append(Spacer(1, 15))

        # === СТОРОНЫ ===
        story.append(Paragraph("2. СТОРОНЫ ДОГОВОРА", style_section))
        story.append(Paragraph("""
            <b>Исполнитель:</b> ООО «ФитИнтел Про», ИНН 7701234567, ОГРН 1157746123456,<br/>
            юридический адрес: 123456, г. Москва, ул. Спортивная, д. 10, офис 501.<br/>
            Телефон: +7 (495) 123-45-67. E-mail: info@fitintel.pro
        """, style_body))
        story.append(Spacer(1, 5))

        birth_str = client.birth_date.strftime("%d.%m.%Y") if client.birth_date else "не указана"
        story.append(Paragraph(f"""
            <b>Заказчик:</b> {client_fio}, дата рождения: {birth_str},<br/>
            телефон: {client.phone or 'не указан'},
            e-mail: {client.email or 'не указан'}
        """, style_body))
        story.append(Spacer(1, 15))

        # === ПРЕДМЕТ ===
        story.append(Paragraph("3. ПРЕДМЕТ ДОГОВОРА", style_section))
        story.append(Paragraph("""
            3.1. Исполнитель обязуется предоставить Заказчику доступ к услугам фитнес-клуба
            в соответствии с выбранным тарифом, а Заказчик обязуется оплатить указанные услуги.<br/>
            3.2. Перечень услуг включает: посещение тренажёрного зала, групповых занятий,
            бассейна, сауны, а также иных услуг в соответствии с действующим прейскурантом.
        """, style_body))
        story.append(Spacer(1, 15))

        # === ПРАВА И ОБЯЗАННОСТИ ===
        story.append(Paragraph("4. ПРАВА И ОБЯЗАННОСТИ СТОРОН", style_section))
        story.append(Paragraph("""
            4.1. Исполнитель обязуется обеспечить надлежащее качество предоставляемых услуг,<br/>
            4.2. Заказчик обязуется соблюдать правила посещения фитнес-клуба,<br/>
            4.3. Заказчик имеет право на заморозку абонемента в случае болезни (при наличии справки).
        """, style_body))
        story.append(Spacer(1, 15))

        # === ОПЛАТА ===
        story.append(Paragraph("5. СТОИМОСТЬ И ПОРЯДОК ОПЛАТЫ", style_section))
        story.append(Paragraph(f"""
            5.1. Стоимость услуг определяется выбранным тарифом и составляет
            <b>{extra.get('amount', '__________')} руб.</b><br/>
            5.2. Оплата производится единовременно или в рассрочку в соответствии с условиями тарифа.
        """, style_body))
        story.append(Spacer(1, 15))

        # === ПЕРСОНАЛЬНЫЕ ДАННЫЕ ===
        if template_id == "consent_personal":
            story.append(Paragraph("6. СОГЛАСИЕ НА ОБРАБОТКУ ПЕРСОНАЛЬНЫХ ДАННЫХ", style_section))
            story.append(Paragraph(f"""
                Я, {client_fio}, даю свое согласие ООО «ФитИнтел Про» на обработку моих персональных данных:<br/>
                — фамилия, имя, отчество;<br/>
                — дата рождения, пол;<br/>
                — контактный телефон, адрес электронной почты;<br/>
                — фотографии (при необходимости для пропускной системы).<br/><br/>
                Согласие дано на срок действия абонемента и может быть отозвано письменным заявлением.
            """, style_body))
        else:
            story.append(Paragraph("6. СРОК ДЕЙСТВИЯ ДОГОВОРА", style_section))
            story.append(Paragraph("""
                6.1. Настоящий договор вступает в силу с момента его подписания обеими сторонами<br/>
                и действует в течение срока, указанного в выбранном тарифе.<br/>
                6.2. Договор может быть расторгнут по соглашению сторон или по инициативе
                Заказчика с возвратом средств пропорционально неоказанным услугам.
            """, style_body))

        story.append(Spacer(1, 30))

        # === ПОДПИСИ ===
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 10))

        sign_data = [
            ["Исполнитель:", "Заказчик:"],
            ["_________________ / _________________", f"_________________ / {client_fio}"],
            [f'ООО «ФитИнтел Про»', f"Дата: {today}"],
        ]
        sign_table = Table(sign_data, colWidths=[8 * cm, 8 * cm])
        sign_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(sign_table)

        # === ФУТЕР ===
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Paragraph(
            f"Документ сгенерирован автоматически системой FitIntel Pro | {today}",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
        ))

        doc.build(story)
        return buffer.getvalue()

    def _render_minimal_pdf(self, template_id: str, client: Client, extra: dict) -> bytes:
        """Fallback: минимальный PDF без reportlab"""
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
        client_fio = f"{client.last_name} {client.first_name}"
        template_info = DOCUMENT_TEMPLATES.get(template_id, {})

        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, height - 80, template_info.get("name", "Документ"))

        c.setFont("Helvetica", 11)
        y = height - 130
        lines = [
            f"Дата: {today}",
            f"Клиент: {client_fio}",
            f"Телефон: {client.phone or 'не указан'}",
            f"E-mail: {client.email or 'не указан'}",
            "",
            "Документ сгенерирован системой FitIntel Pro",
            "Для получения оригинала обратитесь в администрацию клуба.",
        ]
        for line in lines:
            c.drawString(72, y, line)
            y -= 20

        c.save()
        return buffer.getvalue()

    def _make_filename(self, template_id: str, client: Client) -> str:
        prefix = DOCUMENT_TEMPLATES.get(template_id, {}).get("filename_prefix", "doc")
        fio = f"{client.last_name}_{client.first_name}".lower().replace(" ", "_")
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{prefix}_{fio}_{today}_{uuid4().hex[:6]}.pdf"

    @staticmethod
    def _serialize_doc(doc: Document) -> dict:
        return {
            "id": str(doc.id),
            "client_id": str(doc.client_id) if doc.client_id else None,
            "doc_type": doc.doc_type,
            "template_id": doc.template_id,
            "title": doc.title,
            "filename": doc.filename,
            "content_type": doc.content_type,
            "file_size": doc.file_size,
            "status": doc.status,
            "signed_at": doc.signed_at.isoformat() if doc.signed_at else None,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
