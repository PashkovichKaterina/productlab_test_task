import openpyxl
import logging
import asyncio
import aiohttp
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger('django')


class ProductAPIView(APIView):
    @classmethod
    def post(cls, request):
        cls.__validate(request)

        article = request.data['article']
        response_body = asyncio.run(cls.__get_products_data(article))
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

    @classmethod
    async def __get_products_data(cls, article):
        products_data = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            if isinstance(article, UploadedFile):
                workbook = openpyxl.load_workbook(article.file)
                worksheet = workbook.active
                first_column = worksheet['A']
                for cell in first_column:
                    cls.__add_task(session, tasks, cell.value)
            else:
                cls.__add_task(session, tasks, article)

            products_result = await asyncio.gather(*tasks)
            products_data.extend([data for data in products_result if data is not None])

        return products_data if len(products_data) != 1 else products_data[0]

    @classmethod
    def __add_task(cls, session, tasks, article):
        task = asyncio.ensure_future(cls.__parse_product_data(session, article))
        tasks.append(task)

    @staticmethod
    async def __parse_product_data(session, article):
        try:
            async with session.get(f'https://wbx-content-v2.wbstatic.net/ru/{article}.json') as response:
                if response.status == status.HTTP_200_OK:
                    result = await response.json()
                    article = result.get('nm_id')
                    brand = result.get('selling').get('brand_name')
                    title = result.get('imt_name')
                    return {'Article': article, 'Brand': brand, 'Title': title}
                else:
                    logger.info(f'Response code {response.status} for getting product data with article {article}')
        except aiohttp.ClientError as error:
            logger.info(f'Error occurred while reading product data: {error}')
