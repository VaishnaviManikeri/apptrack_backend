import logging
from datetime import datetime, timezone

from bson import ObjectId
from django.core.exceptions import ImproperlyConfigured
from pymongo.errors import (
    ConfigurationError,
    OperationFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .mongo import get_applications_collection
from .serializers import ApplicationSerializer


logger = logging.getLogger(__name__)


def serialize_document(document):
    document["id"] = str(document.pop("_id"))
    for field in ("createdAt", "updatedAt"):
        value = document.get(field)
        if isinstance(value, datetime):
            document[field] = value.isoformat()
    return document


def mongo_error_response(error):
    logger.exception("MongoDB request failed", exc_info=error)
    if isinstance(error, ConfigurationError):
        detail = (
            "MongoDB connection string is invalid. Check the MONGODB_URI format "
            "in backend/.env."
        )
    elif isinstance(error, OperationFailure):
        detail = (
            "MongoDB rejected the database credentials or permissions. Check the "
            "Atlas database user and the encoded username/password in backend/.env."
        )
    elif isinstance(error, ServerSelectionTimeoutError):
        detail = (
            "Could not reach MongoDB Atlas. Check that the cluster is running, "
            "your current IP is allowed in Atlas Network Access, and the cluster "
            "hostname in MONGODB_URI is correct."
        )
    else:
        detail = (
            "MongoDB request failed. Check MONGODB_URI, Atlas network access, "
            "and database user permissions."
        )
    return Response(
        {"detail": detail},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            get_applications_collection().database.command("ping")
        except ImproperlyConfigured as error:
            logger.error("MongoDB configuration is incomplete: %s", error)
            return Response(
                {"detail": str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except PyMongoError as error:
            return mongo_error_response(error)
        return Response({"status": "ok", "database": "connected"})


class ApiRootView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            {
                "health": "/api/health/",
                "auth": {
                    "register": "/api/auth/register/",
                    "login": "/api/auth/login/",
                    "refresh": "/api/auth/refresh/",
                    "current_user": "/api/auth/me/",
                },
                "applications": "/api/applications/",
            }
        )


class ApplicationListCreateView(APIView):
    def get(self, request):
        try:
            collection = get_applications_collection()
            documents = collection.find({"ownerId": str(request.user.pk)}).sort(
                "createdAt", -1
            )
            return Response([serialize_document(document) for document in documents])
        except ImproperlyConfigured as error:
            logger.error("MongoDB configuration is incomplete: %s", error)
            return Response(
                {"detail": str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except PyMongoError as error:
            return mongo_error_response(error)

    def post(self, request):
        serializer = ApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        now = datetime.now(timezone.utc)
        document = {
            **serializer.validated_data,
            "ownerId": str(request.user.pk),
            "createdAt": now,
            "updatedAt": now,
        }
        try:
            result = get_applications_collection().insert_one(document)
            document["_id"] = result.inserted_id
            return Response(
                serialize_document(document),
                status=status.HTTP_201_CREATED,
            )
        except ImproperlyConfigured as error:
            logger.error("MongoDB configuration is incomplete: %s", error)
            return Response(
                {"detail": str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except PyMongoError as error:
            return mongo_error_response(error)


class ApplicationDetailView(APIView):
    def get_document_id(self, application_id):
        if not ObjectId.is_valid(application_id):
            raise ValidationError({"id": "Application id must be a valid MongoDB ObjectId."})
        return ObjectId(application_id)

    def get(self, request, application_id):
        document_id = self.get_document_id(application_id)
        try:
            document = get_applications_collection().find_one(
                {"_id": document_id, "ownerId": str(request.user.pk)}
            )
        except ImproperlyConfigured as error:
            logger.error("MongoDB configuration is incomplete: %s", error)
            return Response(
                {"detail": str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except PyMongoError as error:
            return mongo_error_response(error)
        if document is None:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(serialize_document(document))

    def patch(self, request, application_id):
        document_id = self.get_document_id(application_id)
        serializer = ApplicationSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updates = {
            **serializer.validated_data,
            "updatedAt": datetime.now(timezone.utc),
        }
        try:
            collection = get_applications_collection()
            result = collection.update_one(
                {"_id": document_id, "ownerId": str(request.user.pk)},
                {"$set": updates},
            )
            if result.matched_count == 0:
                return Response(
                    {"detail": "Application not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            document = collection.find_one(
                {"_id": document_id, "ownerId": str(request.user.pk)}
            )
            return Response(serialize_document(document))
        except ImproperlyConfigured as error:
            logger.error("MongoDB configuration is incomplete: %s", error)
            return Response(
                {"detail": str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except PyMongoError as error:
            return mongo_error_response(error)

    def delete(self, request, application_id):
        document_id = self.get_document_id(application_id)
        try:
            result = get_applications_collection().delete_one(
                {"_id": document_id, "ownerId": str(request.user.pk)}
            )
        except ImproperlyConfigured as error:
            logger.error("MongoDB configuration is incomplete: %s", error)
            return Response(
                {"detail": str(error)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except PyMongoError as error:
            return mongo_error_response(error)
        if result.deleted_count == 0:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
