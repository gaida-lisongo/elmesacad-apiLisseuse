from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Metrics(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    categories: int
    documents: int
    pages: int


class RechargeStored(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    status: Literal["pending", "paid", "failed", "completed"]
    credits: int
    order_number: str = Field(alias="orderNumber")
    created_at: datetime = Field(alias="ceatedAt")
    updated_at: datetime = Field(alias="updatedAt")


class User(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    matricule: str
    mail: str
    credits: float
    recharges: list[RechargeStored]
    metrics: Metrics


class UserCreate(BaseModel):
    matricule: str
    mail: str
    credits: float = 0


class AuthorBioSection(BaseModel):
    title: str
    content: list[str]


class AuthorBlock(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    photo: Optional[str] = None
    email: str
    bio_sections: list[AuthorBioSection] = Field(alias="descriontion")


class DocDescriptionBlock(BaseModel):
    title: str
    content: list[str]


class DocumentPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: str
    comment: str
    index: int
    is_read: bool = Field(alias="isRead")


class DocumentCreatePayload(BaseModel):
    """Payload PUT /author/create-document — les URLs des pages sont recalculées côté serveur."""

    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, alias="_id")
    reference: str
    categorie: str
    author: AuthorBlock
    user_id: str = Field(alias="userId")
    total_pages: int = Field(alias="total_pages")
    title: str
    description: list[DocDescriptionBlock]
    pages: list[DocumentPage] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class Category(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    reference: str
    designation: str
    tags: list[str]


class AdminCategoryUpsert(BaseModel):
    reference: str
    designation: str
    tags: list[str] = Field(default_factory=list)


class RechargeCreate(BaseModel):
    status: Literal["pending", "paid", "failed", "completed"]
    credits: int
    order_number: str = Field(alias="orderNumber")


class UserRechargeBody(BaseModel):
    user_id: Optional[str] = Field(default=None, alias="userId")
    matricule: Optional[str] = None
    recharge: RechargeCreate


class ReaderProgressBody(BaseModel):
    user_id: str = Field(alias="userId")
    document_id: str = Field(alias="documentId")
    new_page: Annotated[int, Field(alias="newPage", ge=0)]


class PdfUploadResponse(BaseModel):
    reference: str
    total_pages: int


class UploadPdfForm(BaseModel):
    reference: str
