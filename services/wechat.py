"""
微信公众号图片工具服务
封装下载、去水印、视频生成功能
"""
import os
import re
import sys
import json
import subprocess
import base64
import asyncio
from pathlib import Path
from typing import Optional
import threading


# 原始脚本所在目录（当前项目根目录）
TOOLS_DIR = Path(__file__).resolve().parent.parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


class WeChatDownloader:
    """微信公众号文章图片下载"""

    def __init__(self, work_dir: str = "wechat_articles"):
        self.work_dir = TOOLS_DIR / work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def download_article(self, url: str, output_dir: Optional[str] = None) -> dict:
        """下载单篇文章的所有图片"""
        from download_wechat_images import download_article_images

        out = str(output_dir or self.work_dir)
        try:
            count, article_name = download_article_images(url, output_dir=out)
            return {"status": "ok", "output_dir": os.path.join(out, article_name), "result": count}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def download_all(self, account_url: str, max_articles: int = 0) -> dict:
        """下载公众号所有文章"""
        from download_all_articles import download_all_articles

        try:
            result = download_all_articles(
                account_url,
                output_dir=str(self.work_dir),
                max_articles=max_articles if max_articles > 0 else None,
            )
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_articles(self) -> list:
        """列出已下载的文章"""
        if not self.work_dir.exists():
            return []
        articles = []
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        for d in sorted(self.work_dir.iterdir()):
            if d.is_dir() and (d / "images").exists():
                img_count = len(list((d / "images").iterdir()))
                has_new = (d / "images_new").exists()
                articles.append({
                    "name": d.name,
                    "path": str(d),
                    "image_count": img_count,
                    "processed": has_new,
                })
        # 兼容旧结构：如果 work_dir 根目录直接有图片（平铺），也显示
        flat_imgs = [f for f in self.work_dir.iterdir()
                     if f.is_file() and f.suffix.lower() in exts]
        if flat_imgs and not articles:
            articles.append({
                "name": self.work_dir.name,
                "path": str(self.work_dir),
                "image_count": len(flat_imgs),
                "processed": (self.work_dir / "images_new").exists(),
            })
        return articles


class WatermarkRemover:
    """LaMa 深度学习去水印"""

    def __init__(self):
        self._lama_model = None
        self._lama_available = None

    def remove_folder(
        self, article_dir: str, preset: str = "medium", force: bool = False
    ) -> dict:
        """对一个文章目录执行批量去水印"""
        from batch_remove_watermark import BatchWatermarkRemover

        try:
            remover = BatchWatermarkRemover(str(TOOLS_DIR / "wechat_articles"))
            full_path = str(TOOLS_DIR / "wechat_articles" / article_dir)
            ok, fail = remover.process_article(full_path, preset=preset, force=force)
            return {"status": "ok", "success": ok, "failed": fail}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def remove_single(
        self, image_path: str, preset: str = "medium", output_path: Optional[str] = None
    ) -> dict:
        """对单张图片去水印"""
        from batch_remove_watermark import read_image, remove_watermark, write_image

        try:
            img = read_image(image_path)
            if img is None:
                return {"status": "error", "message": "无法读取图片"}
            result, _ = remove_watermark(img, preset)
            if output_path is None:
                p = Path(image_path)
                output_path = str(p.parent / "images_new" / p.name)
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            write_image(output_path, result)
            return {"status": "ok", "output": output_path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_status(self, article_name: str) -> dict:
        """查看文章处理进度"""
        article_dir = TOOLS_DIR / "wechat_articles" / article_name
        log_path = article_dir / "processed_images.txt"
        images_dir = article_dir / "images"
        out_dir = article_dir / "images_new"

        total = len(list(images_dir.glob("*.jpg"))) if images_dir.exists() else 0
        processed = 0
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8") as f:
                processed = sum(
                    1 for line in f if line.strip() and not line.startswith("#") and not line.startswith("=")
                )

        return {
            "total": total,
            "processed": processed,
            "complete": processed >= total and total > 0,
        }


class VideoGenerator:
    """图片组转短视频"""

    def generate_script(self, article_name: str, resolution: Optional[str] = None) -> dict:
        """AI 分析图片+文章内容，自动筛选图片并生成视频剧本

        流程：
        1. 尺寸过滤：按目标分辨率裁剪/剔除变形图片
        2. AI 筛选：分析所有图片，去掉广告和无意义图片
        3. AI 生成剧本：为保留的图片生成旁白文字
        """
        from srcpy.config import settings
        from srcpy.services.ai_provider import AIProviderFactory
        from PIL import Image

        article_dir = TOOLS_DIR / "wechat_articles" / article_name
        images_dir = article_dir / "images"
        content_file = article_dir / "content.txt"
        script_file = article_dir / "script.txt"
        filtered_file = article_dir / "filtered_images.txt"

        if not images_dir.exists():
            return {"status": "error", "message": "images 目录不存在"}

        # 解析目标分辨率
        target_w, target_h = 1920, 1080
        if resolution and "x" in resolution.lower():
            try:
                target_w, target_h = [int(x) for x in resolution.lower().split("x")]
            except ValueError:
                pass

        # ---- 第一步：读取所有图片 + 尺寸过滤 ----
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        all_img_files = sorted(
            f for f in images_dir.iterdir() if f.suffix.lower() in exts
        )
        if not all_img_files:
            return {"status": "error", "message": "images 目录无图片"}

        kept_files = []
        skipped_small = 0
        skipped_ratio = 0
        target_ratio = target_w / target_h

        for img_path in all_img_files:
            try:
                with Image.open(img_path) as img:
                    w, h = img.size
            except Exception:
                skipped_small += 1
                continue

            # 太小的图片跳过（短边 < 200px）
            if min(w, h) < 200:
                skipped_small += 1
                continue

            # 宽高比差异太大的跳过（> 50% 偏离目标比例）
            img_ratio = w / h if h > 0 else 0
            if img_ratio > 0 and abs(img_ratio - target_ratio) / target_ratio > 0.5:
                skipped_ratio += 1
                continue

            kept_files.append(img_path)

        if not kept_files:
            return {"status": "error", "message": "所有图片都被尺寸过滤掉了"}

        # 限制数量
        max_images = 20
        if len(kept_files) > max_images:
            step = len(kept_files) // max_images
            kept_files = kept_files[::step][:max_images]

        # ---- 第二步：AI 筛选（去广告/无意义图片） ----
        provider_type = settings.ai.default_provider
        if provider_type == "google":
            return {"status": "error", "message": "Google Gemini 暂不支持视觉分析，请切换到其他 AI 提供商"}

        filter_prompt = """分析这些图片，判断哪些适合用于视频旁白。

请为每张图片返回 JSON 数组，格式：
[{"index": 0, "keep": true, "reason": "", "description": "简短描述图片内容"}, ...]

keep=true 表示保留，keep=false 表示剔除。
description 用中文简短描述图片内容（10-20字），如"城市夜景全景"、"产品展示图"。

剔除标准：
- 广告、二维码、公众号名片
- 纯文字截图、聊天记录截图
- 模糊、水印严重、无实际内容
- 重复或高度相似的图片
- 表情包、装饰性元素

保留标准：
- 有实际场景、人物、风景
- 有信息价值的图表或截图
- 文章核心内容配图

只输出 JSON，不要其他内容。"""

        # 构建 AI 消息
        filter_parts = []
        for img_path in kept_files:
            img_data = base64.b64encode(img_path.read_bytes()).decode()
            mime = "image/jpeg"
            if img_path.suffix.lower() == ".png":
                mime = "image/png"
            elif img_path.suffix.lower() == ".webp":
                mime = "image/webp"

            if provider_type == "anthropic":
                filter_parts.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": img_data}
                })
            else:
                filter_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{img_data}"}
                })

        filter_parts.append({"type": "text", "text": filter_prompt})
        messages = [{"role": "user", "content": filter_parts}]

        provider = AIProviderFactory.create(provider_type)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            filter_result = loop.run_until_complete(
                provider.chat(messages, max_tokens=4096)
            )
        except Exception as e:
            loop.close()
            return {"status": "error", "message": f"AI 筛选调用失败: {e}"}

        # 解析 AI 筛选结果
        try:
            # 提取 JSON 部分
            json_match = re.search(r'\[.*\]', filter_result, re.DOTALL)
            if json_match:
                decisions = json.loads(json_match.group())
            else:
                decisions = json.loads(filter_result)
        except (json.JSONDecodeError, TypeError):
            # 解析失败则保留所有
            decisions = [{"index": i, "keep": True} for i in range(len(kept_files))]

        # 应用筛选
        final_files = []
        removed_by_ai = 0
        for i, dec in enumerate(decisions):
            if i >= len(kept_files):
                break
            if dec.get("keep", True):
                final_files.append(kept_files[i])
            else:
                removed_by_ai += 1

        # 如果 AI 全删了或解析异常，保留全部
        if not final_files:
            final_files = kept_files

        # 保存筛选后的图片列表
        filtered_file.write_text(
            "\n".join(f.name for f in final_files), encoding="utf-8"
        )

        # 保存图片元数据（uid, 文件名, 内容描述, 文件大小）
        meta_file = article_dir / "images_meta.txt"
        meta_lines = ["# uid | 文件名 | 内容描述 | 文件大小"]
        for i, img_path in enumerate(kept_files):
            uid = f"img_{i:03d}"
            name = img_path.name
            size_kb = img_path.stat().st_size / 1024
            size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"
            # 从 AI 决策中获取描述
            desc = ""
            if i < len(decisions):
                desc = decisions[i].get("description", "")
            if not desc:
                desc = "（无描述）"
            kept = "✓" if any(f.name == name for f in final_files) else "✗"
            meta_lines.append(f"{uid} | {name} | {desc} | {size_str} | {kept}")
        meta_file.write_text("\n".join(meta_lines), encoding="utf-8")

        # ---- 第三步：为保留的图片生成剧本 ----
        article_text = ""
        if content_file.exists():
            article_text = content_file.read_text(encoding="utf-8")

        script_prompt = f"""你是一个视频旁白编剧。根据以下微信公众号文章内容和配图，为每张图片生成一句简短的旁白文字（用于 TTS 配音和字幕）。

要求：
1. 每行对应一张图片，按顺序排列
2. 每句 15-40 字，口语化，适合朗读
3. 语气自然流畅，像在给朋友讲故事
4. 不要加编号、不要加引号、不要加多余标点
5. 直接输出纯文本，每句一行
6. 第一句可以是引子/开场白，最后一句可以是总结

文章内容（参考）：
{article_text[:3000]}"""

        script_parts = []
        for img_path in final_files:
            img_data = base64.b64encode(img_path.read_bytes()).decode()
            mime = "image/jpeg"
            if img_path.suffix.lower() == ".png":
                mime = "image/png"
            elif img_path.suffix.lower() == ".webp":
                mime = "image/webp"

            if provider_type == "anthropic":
                script_parts.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": img_data}
                })
            else:
                script_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{img_data}"}
                })

        script_parts.append({"type": "text", "text": script_prompt})
        messages = [{"role": "user", "content": script_parts}]

        try:
            script_result = loop.run_until_complete(
                provider.chat(messages, max_tokens=4096)
            )
        except Exception as e:
            return {"status": "error", "message": f"AI 剧本生成调用失败: {e}"}
        finally:
            loop.close()

        # 清理结果
        lines = []
        for line in script_result.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r'^\d+[\.\)、]\s*', '', line)
            line = line.strip('""''「」『』')
            if line:
                lines.append(line)

        if not lines:
            return {"status": "error", "message": "AI 返回内容为空"}

        script_file.write_text("\n".join(lines), encoding="utf-8")

        # 输出剧本详情：每句旁白对应的图片和提示词
        detail_file = article_dir / "script_detail.txt"
        detail_lines = [
            "# 剧本详情",
            "# 格式: 序号 | 图片文件 | 旁白文字 | 生成提示词",
            "=" * 60,
        ]
        for i, line in enumerate(lines):
            img_name = final_files[i].name if i < len(final_files) else "无"
            prompt_text = f"根据图片和文章内容，为第{i+1}张图片生成旁白"
            detail_lines.append(f"{i+1:03d} | {img_name} | {line} | {prompt_text}")
        detail_file.write_text("\n".join(detail_lines), encoding="utf-8")

        # 输出最终选择的图片到 selected/ 目录
        import shutil
        selected_dir = article_dir / "selected"
        if selected_dir.exists():
            shutil.rmtree(selected_dir)
        selected_dir.mkdir(parents=True, exist_ok=True)
        for img_path in final_files:
            shutil.copy2(img_path, selected_dir / img_path.name)

        return {
            "status": "ok",
            "script_path": str(script_file),
            "meta_path": str(meta_file),
            "detail_path": str(detail_file),
            "selected_dir": str(selected_dir),
            "lines": len(lines),
            "images_total": len(all_img_files),
            "images_filtered_size": skipped_small + skipped_ratio,
            "images_filtered_ai": removed_by_ai,
            "images_final": len(final_files),
        }

    def make_video(
        self,
        article_name: str,
        duration: float = 3.0,
        fps: int = 24,
        transition: str = "fade",
        transition_dur: float = 0.5,
        music_path: Optional[str] = None,
        title: Optional[str] = None,
        title_duration: float = 3.0,
        title_color: str = "white",
        title_font_size: int = 48,
        output_path: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> dict:
        """为一个文章生成短视频"""
        from images_to_video import make_video as _make_video

        article_dir = str(TOOLS_DIR / "wechat_articles" / article_name)
        res = None
        if resolution:
            w, h = resolution.lower().split("x")
            res = (int(w), int(h))

        try:
            result = _make_video(
                image_dir=article_dir,
                output_path=output_path,
                duration=duration,
                fps=fps,
                transition=transition,
                transition_dur=transition_dur,
                music_path=music_path,
                title=title or article_name,
                title_duration=title_duration,
                title_color=title_color,
                title_font_size=title_font_size,
                resolution=res,
            )
            if result:
                return {"status": "ok", "output": result}
            return {"status": "error", "message": "视频生成失败"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def make_video_pro(
        self,
        article_name: str,
        script_path: Optional[str] = None,
        voice: str = "zh-CN-YunxiNeural",
        voice_rate: str = "+0%",
        music_path: Optional[str] = None,
        music_volume: float = 0.3,
        font_size: int = 36,
        fps: int = 24,
        resolution: Optional[str] = None,
        enable_enhance: bool = True,
        enable_kenburns: bool = True,
        enable_crossfade: bool = True,
        enable_vignette: bool = True,
        enable_lightleak: bool = False,
    ) -> dict:
        """专业版视频：剧本 + TTS配音 + 字幕 + 背景音乐"""
        from images_to_video_pro import make_video_pro as _make_video_pro

        article_dir = str(TOOLS_DIR / "wechat_articles" / article_name)
        res = None
        if resolution:
            w, h = resolution.lower().split("x")
            res = (int(w), int(h))

        # 读取筛选后的图片列表
        filtered_images = None
        filtered_file = Path(article_dir) / "filtered_images.txt"
        if filtered_file.exists():
            filtered_images = [
                line.strip() for line in filtered_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        try:
            result = _make_video_pro(
                image_dir=article_dir,
                script_path=script_path,
                voice=voice,
                voice_rate=voice_rate,
                music_path=music_path,
                music_volume=music_volume,
                font_size=font_size,
                fps=fps,
                resolution=res,
                filtered_images=filtered_images,
                enable_enhance=enable_enhance,
                enable_kenburns=enable_kenburns,
                enable_crossfade=enable_crossfade,
                enable_vignette=enable_vignette,
                enable_lightleak=enable_lightleak,
            )
            if result:
                return {"status": "ok", "output": result}
            return {"status": "error", "message": "视频生成失败"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def make_all(
        self,
        duration: float = 3.0,
        transition: str = "fade",
        music_path: Optional[str] = None,
        title: Optional[str] = None,
    ) -> list:
        """为所有文章生成短视频"""
        articles_dir = TOOLS_DIR / "wechat_articles"
        if not articles_dir.exists():
            return []

        results = []
        for d in sorted(articles_dir.iterdir()):
            if d.is_dir() and (d / "images_new").exists():
                r = self.make_video(
                    article_name=d.name,
                    duration=duration,
                    transition=transition,
                    music_path=music_path,
                    title=title,
                )
                results.append({"article": d.name, **r})
        return results
