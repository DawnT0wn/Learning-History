from reportlab.lib import units
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import glob
from pathlib import Path
from pikepdf import Pdf, Rectangle
import sys
import os
import shutil

pdfmetrics.registerFont(TTFont('Songti', 'Songti.ttc')) # 加载中文字体

col = 5  # 每页多少列水印
row = 5  # 每页多少行水印

def GetCustomers():
    customer_list = []
    with open('customers', 'r') as f:
        for line in f.readlines():
            customer_list.append(line.strip())
    return customer_list


def MakeWaterMark(filename):
    # 用一个文件夹存放所有的水印PDF
    water_dir_tmp = 'water_tmp'
    customer_list = GetCustomers()

    water_mark_folder = Path(water_dir_tmp)
    water_mark_folder.mkdir(exist_ok=True)

    for name in customer_list:
        path = str(water_mark_folder / Path(f'{name}.pdf'))
        c = canvas.Canvas(path, pagesize=(200 * units.mm, 200 * units.mm)) # 生成画布，长宽都是200毫米
        c.translate(0.1 * 200 * units.mm, 0.1 * 200 * units.mm)
        c.rotate(45)  # 把水印文字旋转45°
        c.setFont('Songti', 50)  # 字体大小
        c.setStrokeColorRGB(0, 0, 0)  # 设置字体颜色
        c.setFillColorRGB(0, 0, 0)  # 设置填充颜色
        c.setFillAlpha(0.3)  # 设置透明度，越小越透明
        c.drawString(0, 0, f'{name}')
        c.save()

    water_pdf_list = glob.glob(water_dir_tmp + '/*.pdf')
    result = Path('result')
    result.mkdir(exist_ok=True)

    for path in water_pdf_list:
        target = Pdf.open(filename)  # 必须每次重新打开PDF，因为添加水印是inplace的操作
        file = Path(path)
        name = file.stem
        water_mark_pdf = Pdf.open(path)
        water_mark = water_mark_pdf.pages[0]

        for page in target.pages:
            for x in range(col):  # 每一行显示多少列水印
                for y in range(row):  # 每一页显示多少行PDF
                    page.add_overlay(water_mark,
                                     Rectangle(page.trimbox[2] * x / col,
                                               page.trimbox[3] * y / row,
                                               page.trimbox[2] * (x + 1) / col,
                                               page.trimbox[3] * (y + 1) / row))
        only_filename, _ = os.path.splitext(filename)

        result_name = Path('result', f'{only_filename}-{name}.pdf')
        target.save(str(result_name))


if __name__ == '__main__':
    if len (sys.argv) != 2:
        print("参数为文件名")
        exit()

    filename = sys.argv[1]
    MakeWaterMark(filename)