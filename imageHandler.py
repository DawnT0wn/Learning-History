import os
import re
import shutil

# 遍历当前文件夹及其子文件夹
root_folder = "."
target_folder_name = "images"

# 遍历文件夹及子文件夹
for root, dirs, files in os.walk(root_folder):
    # 如果当前目录已经存在 images 子目录，则跳过操作
    if target_folder_name in dirs:
        dirs.remove(target_folder_name)
        continue

    for filename in files:
        if filename.endswith(".md") and filename.lower() != "readme.md":
            md_path = os.path.join(root, filename)
            images_folder = os.path.join(os.path.dirname(md_path), target_folder_name)

            # 创建与 Markdown 文件同名的目录
            new_folder = os.path.join(root, os.path.splitext(filename)[0])
            if not os.path.exists(new_folder):
                os.makedirs(new_folder)

            # 将 Markdown 文件移动到新目录中
            new_md_path = os.path.join(new_folder, filename)
            shutil.move(md_path, new_md_path)

            # 创建 images 子目录
            images_subfolder = os.path.join(new_folder, target_folder_name)
            if not os.path.exists(images_subfolder):
                os.makedirs(images_subfolder)

            # 读取 Markdown 文件内容
            with open(new_md_path, "r") as f:
                content = f.read()

            # 提取图片路径
            image_paths = re.findall(r'\((.*?)\)', content)
            image_paths = [path for path in image_paths if path.startswith("/")]

            # 遍历并复制图片到 images 子目录
            try:
                for idx, image_path in enumerate(image_paths, start=1):
                    image_name = os.path.basename(image_path)
                    image_extension = os.path.splitext(image_name)[1]
                    target_path = os.path.join(images_subfolder, f"{idx}{image_extension}")

                    # 复制图片文件到 images 子目录
                    shutil.copy(image_path, target_path)

                    # 替换 Markdown 文件中的图片路径为相对路径
                    new_image_path = os.path.relpath(target_path, start=os.path.dirname(new_md_path))
                    content = content.replace(image_path, new_image_path)
            except Exception as e:
                print(e)

            # 将更新后的内容写回 Markdown 文件
            with open(new_md_path, "w") as f:
                f.write(content)

print("完成目录创建、文件移动、图片复制和路径替换")
