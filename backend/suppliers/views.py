from bson import ObjectId
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Supplier
from .serializers import SupplierSerializer


def _get_supplier(supplier_id):
    if not ObjectId.is_valid(supplier_id):
        return None
    return Supplier.objects(id=ObjectId(supplier_id)).first()


class SupplierListCreateView(APIView):
    def get(self, request):
        suppliers = Supplier.objects.order_by("-created_at")
        return Response(SupplierSerializer(suppliers, many=True).data)

    def post(self, request):
        serializer = SupplierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supplier = serializer.save()
        return Response(SupplierSerializer(supplier).data, status=status.HTTP_201_CREATED)


class SupplierDetailView(APIView):
    def get(self, request, supplier_id):
        supplier = _get_supplier(supplier_id)
        if not supplier:
            return Response({"detail": "Supplier not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SupplierSerializer(supplier).data)

    def patch(self, request, supplier_id):
        supplier = _get_supplier(supplier_id)
        if not supplier:
            return Response({"detail": "Supplier not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SupplierSerializer(supplier, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, supplier_id):
        supplier = _get_supplier(supplier_id)
        if not supplier:
            return Response({"detail": "Supplier not found."}, status=status.HTTP_404_NOT_FOUND)
        supplier.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
