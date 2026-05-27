"""
微信公众号图片工具服务
封装下载、去水印、视频生成功能
"""
import os
import re
import sys
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

    def generate_script(self, article_name: str) -> dict:
        """用 AI 分析图片+文章内容，自动生成视频剧本"""
        from srcpy.config import settings
        from srcpy.services.ai_provider import AIProviderFactory

        article_dir = TOOLS_DIR / "wechat_articles" / article_name
        images_dir = article_dir / "images"
        content_file = article_dir / "content.txt"
        script_file = article_dir / "script.txt"

        if not images_dir.exists():
            return {"status": "error", "message": "images 目录不存在"}

        # 读取文章内容
        article_text = ""
        if content_file.exists():
            article_text = content_file.read_text(encoding="utf-8")

        # 读取图片列表并转 base64
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        img_files = sorted(
            f for f in images_dir.iterdir() if f.suffix.lower() in exts
        )
        if not img_files:
            return {"status": "error", "message": "images 目录无图片"}

        # 限制图片数量（避免 token 溢出）
        max_images = 20
        if len(img_files) > max_images:
            step = len(img_files) // max_images
            img_files = img_files[::step][:max_images]

        # 构造 vision 消息
        provider_type = settings.ai.default_provider
        if provider_type == "google":
            return {"status": "error", "message": "Google Gemini 暂不支持视觉分析，请切换到其他 AI 提供商"}

        prompt = f"""你是一个视频旁白编剧。根据以下微信公众号文章内容和配图，为每张图片生成一句简短的旁白文字（用于 TTS 配音和字幕）。

要求：
1. 每行对应一张图片，按顺序排列
2. 每句 15-40 字，口语化，适合朗读
3. 语气自然流畅，像在给朋友讲故事
4. 如果是空行则跳过（不要输出空行）
5. 不要加编号、不要加引号、不要加多余标点
6. 直接输出纯文本，每句一行

文章内容（参考）：
{article_text[:3000]}"""

        # 构建消息
        content_parts = []
        for img_path in img_files:
            img_data = base64.b64encode(img_path.read_bytes()).decode()
            mime = "image/jpeg"
            if img_path.suffix.lower() == ".png":
                mime = "image/png"
            elif img_path.suffix.lower() == ".webp":
                mime = "image/webp"

            if provider_type == "anthropic":
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime,
                        "data": img_data,
                    }
                })
            else:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{img_data}"}
                })

        content_parts.append({"type": "text", "text": prompt})

        messages = [{"role": "user", "content": content_parts}]

        # 调用 AI
        try:
            provider = AIProviderFactory.create(provider_type)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    provider.chat(messages, max_tokens=4096)
                )
            finally:
                loop.close()
        except Exception as e:
            return {"status": "error", "message": f"AI 调用失败: {e}"}

        # 清理结果：去除编号、引号等
        lines = []
        for line in result.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # 去掉开头的编号 "1." "1)" "1、" 等
            line = re.sub(r'^\d+[\.\)、]\s*', '', line)
            # 去掉首尾引号
            line = line.strip('""''「」『』')
            if line:
                lines.append(line)

        if not lines:
            return {"status": "error", "message": "AI 返回内容为空"}

        script_file.write_text("\n".join(lines), encoding="utf-8")
        return {"status": "ok", "script_path": str(script_file), "lines": len(lines)}

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
    ) -> dict:
        """专业版视频：剧本 + TTS配音 + 字幕 + 背景音乐"""
        from images_to_video_pro import make_video_pro as _make_video_pro

        article_dir = str(TOOLS_DIR / "wechat_articles" / article_name)
        res = None
        if resolution:
            w, h = resolution.lower().split("x")
            res = (int(w), int(h))

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
