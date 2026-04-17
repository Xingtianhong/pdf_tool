#!/usr/bin/env python3
"""
PDF 工具箱 - 集成以下功能：
1. 去除原页码并添加新页码（覆盖指定区域图片 + 底部居中）
2. 拆分 PDF（按页码范围）
3. 合并 PDF
4. 在指定位置插入 PDF 并重编页码（右下角）
"""

import os
import io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter

# ----------------------------------------------------------------------
# 功能 1：去原页码 + 添加新页码（覆盖指定区域图片 + 底部居中）
# ----------------------------------------------------------------------
def remove_old_and_add_new_pages(input_pdf, image_path, output_pdf, image_rect, bottom_margin=30):
    """
    在 PDF 每页指定位置添加不透明图片（完全覆盖下方内容），并在底部居中加页码。
    image_rect: (左, 上, 右, 下) 坐标（页面左上角为原点，单位点）
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    for page_num, page in enumerate(reader.pages):
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        x0, y0_top, x1, y1_top = image_rect
        # 自动调整超出顶部的矩形
        if y0_top > page_height:
            rect_height = y1_top - y0_top
            new_y0_top = max(0, page_height - rect_height)
            new_y1_top = new_y0_top + rect_height
            if new_y1_top > page_height:
                new_y1_top = page_height
            x0, y0_top, x1, y1_top = x0, new_y0_top, x1, new_y1_top

        # 转换到 reportlab 左下角坐标
        rect_left = x0
        rect_bottom = page_height - y1_top
        rect_width = x1 - x0
        rect_height = y1_top - y0_top

        # 创建覆盖层
        overlay_buffer = io.BytesIO()
        c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

        # 白色填充矩形
        c.setFillColorRGB(1, 1, 1)
        c.rect(rect_left, rect_bottom, rect_width, rect_height, fill=1, stroke=0)

        # 绘制图片
        try:
            img_reader = ImageReader(image_path)
            c.drawImage(img_reader,
                        rect_left, rect_bottom,
                        width=rect_width, height=rect_height,
                        preserveAspectRatio=False)
            print(f"页面 {page_num+1}: 图片已覆盖矩形 ({rect_left:.1f},{rect_bottom:.1f}) 尺寸 {rect_width:.1f}x{rect_height:.1f}")
        except Exception as e:
            print(f"页面 {page_num+1}: 图片绘制失败 - {e}")

        # 添加底部居中页码
        text = f"-{page_num + 1}-"
        font_size = 14
        c.setFont("Helvetica", font_size)
        text_width = c.stringWidth(text, "Helvetica", font_size)
        x_center = (page_width - text_width) / 2
        y_text = bottom_margin
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x_center, y_text, text)

        c.save()
        overlay_buffer.seek(0)
        overlay_page = PdfReader(overlay_buffer).pages[0]
        page.merge_page(overlay_page)
        writer.add_page(page)

    with open(output_pdf, "wb") as f:
        writer.write(f)
    print(f"✅ 已完成！输出文件：{output_pdf}，总页数：{len(writer.pages)}")

# ----------------------------------------------------------------------
# 功能 2：拆分 PDF
# ----------------------------------------------------------------------
def split_pdf(input_pdf, segments):
    """
    segments: 列表，每个元素为 (起始页, 结束页, 输出文件名) 页码从1开始
    """
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    print(f"源文件总页数: {total_pages}")

    for start_page, end_page, output_file in segments:
        start_idx = start_page - 1
        end_idx = min(end_page, total_pages)
        if start_idx >= total_pages:
            print(f"跳过 {output_file}: 起始页超出范围")
            continue
        writer = PdfWriter()
        for i in range(start_idx, end_idx):
            writer.add_page(reader.pages[i])
        with open(output_file, "wb") as f:
            writer.write(f)
        print(f"✅ 保存 {output_file} (第 {start_page}-{end_idx} 页)")

# ----------------------------------------------------------------------
# 功能 3：合并 PDF
# ----------------------------------------------------------------------
def merge_pdfs(pdf_list, output_pdf):
    """
    按列表顺序合并多个 PDF
    """
    writer = PdfWriter()
    for pdf_path in pdf_list:
        if not os.path.exists(pdf_path):
            print(f"⚠️ 文件不存在，跳过: {pdf_path}")
            continue
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)
        print(f"已添加: {pdf_path} ({len(reader.pages)} 页)")
    with open(output_pdf, "wb") as f:
        writer.write(f)
    print(f"✅ 合并完成！输出文件：{output_pdf}，总页数：{len(writer.pages)}")

# ----------------------------------------------------------------------
# 功能 4：插入 PDF 并重编页码（右下角）
# ----------------------------------------------------------------------
def insert_pdf(original_path, insert_path, output_path, insert_after_page):
    """在原始 PDF 的指定页之后插入另一个 PDF，返回临时文件路径（无页码）"""
    reader_orig = PdfReader(original_path)
    reader_ins = PdfReader(insert_path)
    writer = PdfWriter()
    total_orig = len(reader_orig.pages)
    insert_idx = insert_after_page
    if insert_idx < 0:
        insert_idx = 0
    if insert_idx > total_orig:
        insert_idx = total_orig

    for i in range(insert_idx):
        writer.add_page(reader_orig.pages[i])
    for page in reader_ins.pages:
        writer.add_page(page)
    for i in range(insert_idx, total_orig):
        writer.add_page(reader_orig.pages[i])

    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"✅ 合并完成！临时文件：{output_path}，总页数：{len(writer.pages)}")
    return output_path

def add_page_numbers(input_pdf, output_pdf, start_number=1, position="bottom_right"):
    """
    为 PDF 添加页码
    position: "bottom_right" 或 "bottom_center"
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        try:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
        except AttributeError:
            width, height = letter

        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(width, height))
        page_num = start_number + i
        text = str(page_num)
        can.setFont("Helvetica", 10)

        if position == "bottom_right":
            can.drawRightString(width - 40, 30, text)
        elif position == "bottom_center":
            text_width = can.stringWidth(text, "Helvetica", 10)
            can.drawString((width - text_width) / 2, 30, text)
        else:
            can.drawString(50, 30, text)  # 左下角默认

        can.save()
        packet.seek(0)
        overlay_page = PdfReader(packet).pages[0]
        page.merge_page(overlay_page)
        writer.add_page(page)

    with open(output_pdf, "wb") as f:
        writer.write(f)
    print(f"✅ 页码添加完成！输出文件：{output_pdf}，总页数：{len(writer.pages)}")

def insert_and_repage(original_path, insert_path, output_pdf, insert_after_page, start_number=1):
    """插入并添加连续页码（右下角）"""
    temp_merged = "temp_merged_for_repage.pdf"
    insert_pdf(original_path, insert_path, temp_merged, insert_after_page)
    add_page_numbers(temp_merged, output_pdf, start_number=start_number, position="bottom_right")
    if os.path.exists(temp_merged):
        os.remove(temp_merged)
        print("🗑️ 已删除临时文件")

# ----------------------------------------------------------------------
# 交互菜单
# ----------------------------------------------------------------------
def print_menu():
    print("\n" + "="*50)
    print(" PDF 工具箱")
    print("="*50)
    print("1. 去除原页码并添加新页码（覆盖图片 + 底部居中）")
    print("2. 拆分 PDF（按页码范围）")
    print("3. 合并多个 PDF")
    print("4. 插入另一个 PDF 并重编页码（右下角）")
    print("0. 退出")
    print("="*50)

def get_rect_from_user():
    """获取用户输入的矩形坐标 (左,上,右,下)"""
    print("请输入图片覆盖矩形的坐标（单位：点，1点=1/72英寸）")
    print("页面左上角为原点 (0,0)，向右为 X 正，向下为 Y 正")
    try:
        left = float(input("  左 (X1): "))
        top = float(input("  上 (Y1): "))
        right = float(input("  右 (X2): "))
        bottom = float(input("  下 (Y2): "))
        return (left, top, right, bottom)
    except ValueError:
        print("输入无效，使用默认矩形 (1, 1095, 825, 1169)")
        return (1, 1095, 825, 1169)

def get_split_segments():
    """交互式获取拆分段落"""
    segments = []
    print("输入拆分段落，每段一行：起始页 结束页 输出文件名（空格分隔）")
    print("例如：1 10 part1.pdf")
    print("输入空行结束")
    while True:
        line = input(">>> ").strip()
        if not line:
            break
        parts = line.split()
        if len(parts) != 3:
            print("格式错误，需要三个字段：起始页 结束页 输出文件名")
            continue
        try:
            start = int(parts[0])
            end = int(parts[1])
            fname = parts[2]
            segments.append((start, end, fname))
        except ValueError:
            print("起始页和结束页必须是数字")
    return segments

def get_pdf_list():
    """获取要合并的 PDF 列表"""
    print("请输入要合并的 PDF 文件路径，每行一个，输入空行结束")
    files = []
    while True:
        path = input(">>> ").strip()
        if not path:
            break
        if os.path.exists(path):
            files.append(path)
        else:
            print(f"文件不存在: {path}")
    return files

def main():
    # 检查依赖
    try:
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas
    except ImportError as e:
        print("❌ 缺少必要库，请运行：pip install pypdf reportlab")
        return

    while True:
        print_menu()
        choice = input("请选择功能 (0-4): ").strip()
        if choice == "0":
            print("再见！")
            break
        elif choice == "1":
            input_pdf = input("输入 PDF 文件路径: ").strip()
            if not os.path.exists(input_pdf):
                print("文件不存在！")
                continue
            image_path = input("输入图片文件路径 (如 cover.png): ").strip()
            if not os.path.exists(image_path):
                print("图片文件不存在！")
                continue
            output_pdf = input("输出 PDF 文件名: ").strip()
            if not output_pdf:
                output_pdf = "output_with_new_pages.pdf"
            rect = get_rect_from_user()
            try:
                remove_old_and_add_new_pages(input_pdf, image_path, output_pdf, rect)
            except Exception as e:
                print(f"操作失败: {e}")
        elif choice == "2":
            input_pdf = input("输入要拆分的 PDF 文件路径: ").strip()
            if not os.path.exists(input_pdf):
                print("文件不存在！")
                continue
            segments = get_split_segments()
            if not segments:
                print("未输入任何段落，返回菜单")
                continue
            try:
                split_pdf(input_pdf, segments)
            except Exception as e:
                print(f"拆分失败: {e}")
        elif choice == "3":
            pdf_list = get_pdf_list()
            if len(pdf_list) < 2:
                print("至少需要两个 PDF 文件才能合并")
                continue
            output_pdf = input("输出合并后的文件名: ").strip()
            if not output_pdf:
                output_pdf = "merged.pdf"
            try:
                merge_pdfs(pdf_list, output_pdf)
            except Exception as e:
                print(f"合并失败: {e}")
        elif choice == "4":
            original = input("原始 PDF 文件路径: ").strip()
            if not os.path.exists(original):
                print("文件不存在！")
                continue
            insert = input("要插入的 PDF 文件路径: ").strip()
            if not os.path.exists(insert):
                print("文件不存在！")
                continue
            try:
                after_page = int(input("在第几页之后插入 (1-based): ").strip())
            except ValueError:
                print("页码必须是整数")
                continue
            output_pdf = input("输出文件名: ").strip()
            if not output_pdf:
                output_pdf = "inserted_and_numbered.pdf"
            try:
                insert_and_repage(original, insert, output_pdf, after_page)
            except Exception as e:
                print(f"操作失败: {e}")
        else:
            print("无效选项，请输入 0-4")

if __name__ == "__main__":
    main()
