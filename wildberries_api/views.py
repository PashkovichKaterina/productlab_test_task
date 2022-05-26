import openpyxl
import logging
import requests
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger('django')


class ProductAPIView(APIView):
    @classmethod
    def get(cls, request):
        cls.__validate(request)

        article = request.data['article']
        if isinstance(article, UploadedFile):
            workbook = openpyxl.load_workbook(article.file)
            worksheet = workbook.active
            first_column = worksheet['A']

            response_body = []
            for cell in first_column:
                product_data = cls.__parse_product_data(cell.value)
                if product_data is not None:
                    response_body.append(product_data)
        else:
            response_body = cls.__parse_product_data(article)

        response_status = status.HTTP_200_OK
        return Response(response_body, status=response_status)

    @staticmethod
    def __validate(request):
        if 'article' not in request.data:
            raise ValidationError('The parameter \'article\' is required')

        article = request.data['article']
        xlsx_content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        if isinstance(article, UploadedFile) and article.content_type != xlsx_content_type:
            raise ValidationError('Unable file format')

    @staticmethod
    def __parse_product_data(article):
        try:
            response = requests.get(f'https://wbx-content-v2.wbstatic.net/ru/{article}.json')
            if response.status_code == status.HTTP_200_OK:
                result = response.json()
                article = result.get('nm_id')
                brand = result.get('selling').get('brand_name')
                title = result.get('imt_name')
                return {'Article': article, 'Brand': brand, 'Title': title}
            else:
                logger.info(f'Response code {response.status_code} for getting product data with article {article}')
        except requests.exceptions.RequestException as exception:
            logger.info(f'Exception occurred while reading product data: {exception}')
