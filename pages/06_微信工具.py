"""
微信公众号图片工具
下载文章图片 → 去水印 → 生成短视频
"""
import streamlit as st
from pathlib import Path
import sys
import os

# 确保服务可导入
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from services.wechat import WeChatDownloader, WatermarkRemover, VideoGenerator, TOOLS_DIR


def render_wechat_page():
    st.set_page_config(page_title="微信工具", page_icon="📱", layout="wide")

    st.title("📱 微信公众号图片工具")
    st.caption("下载文章图片 → 去水印 → 生成短视频")

    tab1, tab2, tab3 = st.tabs(["📥 下载图片", "🖼️ 去水印", "🎬 生成视频"])

    # ==================== Tab 1: 下载 ====================
    with tab1:
        st.subheader("下载微信公众号文章图片")

        download_mode = st.radio(
            "下载模式",
            ["单篇文章", "整个公众号"],
            horizontal=True,
            key="dl_mode",
        )

        if download_mode == "单篇文章":
            url = st.text_input(
                "文章链接",
                placeholder="https://mp.weixin.qq.com/s/...",
                key="article_url",
            )
            if st.button("开始下载", key="btn_download_article", type="primary"):
                if not url.strip():
                    st.error("请输入文章链接")
                else:
                    with st.spinner("正在下载..."):
                        downloader = WeChatDownloader()
                        result = downloader.download_article(url)
                    if result["status"] == "ok":
                        st.success(f"下载完成！输出目录: {result['output_dir']}")
                    else:
                        st.error(f"下载失败: {result['message']}")
        else:
            account_url = st.text_input(
                "公众号文章列表页链接",
                placeholder="https://mp.weixin.qq.com/mp/profile_ext?...",
                key="account_url",
            )
            max_articles = st.number_input(
                "最多下载文章数（0=全部）", min_value=0, value=0, key="max_articles"
            )
            if st.button("开始批量下载", key="btn_download_all", type="primary"):
                if not account_url.strip():
                    st.error("请输入公众号链接")
                else:
                    with st.spinner("正在批量下载..."):
                        downloader = WeChatDownloader()
                        result = downloader.download_all(account_url, max_articles)
                    if result["status"] == "ok":
                        st.success("批量下载完成！")
                    else:
                        st.error(f"下载失败: {result['message']}")

        # 显示已下载文章列表
        st.divider()
        st.subheader("已下载的文章")
        downloader = WeChatDownloader()
        articles = downloader.list_articles()

        if not articles:
            st.info("暂无已下载的文章")
        else:
            for art in articles:
                col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
                with col1:
                    st.write(f"📁 {art['name']}")
                with col2:
                    st.caption(f"{art['image_count']} 张图片")
                with col3:
                    if art["processed"]:
                        st.success("已去水印")
                    else:
                        st.warning("未处理")
                with col4:
                    if st.button("去水印", key=f"goto_wm_{art['name']}"):
                        st.session_state["selected_article"] = art["name"]
                        st.rerun()

    # ==================== Tab 2: 去水印 ====================
    with tab2:
        st.subheader("批量去水印")

        # 选择文章
        downloader = WeChatDownloader()
        articles = downloader.list_articles()
        article_names = [a["name"] for a in articles]

        if not article_names:
            st.info("暂无可处理的文章，请先在「下载图片」标签页下载文章")
        else:
            selected = st.selectbox(
                "选择文章",
                article_names,
                index=article_names.index(st.session_state.get("selected_article", article_names[0]))
                if st.session_state.get("selected_article") in article_names
                else 0,
                key="wm_article",
            )

            preset = st.selectbox(
                "修复强度",
                ["light", "medium", "heavy"],
                index=1,
                format_func=lambda x: {
                    "light": "轻度 - 适合淡水印",
                    "medium": "中度 - 推荐",
                    "heavy": "强力 - 深水印",
                }[x],
                key="wm_preset",
            )

            force = st.checkbox("强制重新处理（覆盖已有结果）", key="wm_force")

            # 显示当前状态
            remover = WatermarkRemover()
            status = remover.get_status(selected)
            st.info(f"总计 {status['total']} 张，已处理 {status['processed']} 张")

            if st.button("开始去水印", key="btn_watermark", type="primary"):
                with st.spinner(f"正在处理 {selected}..."):
                    result = remover.remove_folder(
                        selected, preset=preset, force=force
                    )
                if result["status"] == "ok":
                    st.success(f"处理完成！成功 {result['success']} 张，失败 {result['failed']} 张")
                else:
                    st.error(f"处理失败: {result['message']}")

    # ==================== Tab 3: 生成视频 ====================
    with tab3:
        st.subheader("图片组 → 短视频")

        downloader = WeChatDownloader()
        articles = downloader.list_articles()
        processed_articles = [a["name"] for a in articles if a["processed"]]

        if not processed_articles:
            st.info("暂无已去水印的文章，请先在「去水印」标签页处理文章")
        else:
            selected_video = st.selectbox(
                "选择文章",
                processed_articles,
                key="video_article",
            )

            video_mode = st.radio(
                "视频模式",
                ["专业版（剧本+配音+字幕）", "基础版（图片轮播）"],
                horizontal=True,
                key="video_mode",
            )

            if video_mode == "专业版（剧本+配音+字幕）":
                st.markdown("##### 专业版设置")

                # 剧本来源选择
                script_source = st.radio(
                    "剧本来源",
                    ["AI 自动生成", "手动上传"],
                    horizontal=True,
                    key="script_source",
                )

                script_path = None
                script_file = None
                if script_source == "AI 自动生成":
                    st.caption("AI 将分析文章图片和文字内容，为每张图片生成一句旁白")
                    if st.button("生成剧本", key="btn_gen_script"):
                        with st.spinner("AI 正在分析图片并生成剧本..."):
                            gen = VideoGenerator()
                            result = gen.generate_script(selected_video)
                        if result["status"] == "ok":
                            st.success(f"剧本生成完成！共 {result['lines']} 句")
                            script_path = result["script_path"]
                            # 显示生成的剧本预览
                            with open(script_path, "r", encoding="utf-8") as f:
                                script_content = f.read()
                            with st.expander("预览剧本", expanded=True):
                                st.text_area("script_preview", script_content, height=150, disabled=True, key="script_preview")
                        else:
                            st.error(f"生成失败: {result['message']}")
                    else:
                        # 尝试使用已生成的 script.txt
                        existing_script = TOOLS_DIR / "wechat_articles" / selected_video / "script.txt"
                        if existing_script.exists():
                            script_path = str(existing_script)
                            with st.expander("已生成的剧本（点击展开）", expanded=False):
                                st.text_area("script_preview", existing_script.read_text(encoding="utf-8"), height=150, disabled=True, key="script_preview")
                else:
                    script_file = st.file_uploader(
                        "上传剧本文件（.txt，每行对应一张图片）",
                        type=["txt"],
                        key="vid_script",
                    )

                col1, col2 = st.columns(2)
                with col1:
                    voice = st.selectbox(
                        "配音语音",
                        [
                            "zh-CN-YunxiNeural",
                            "zh-CN-XiaoxiaoNeural",
                            "zh-CN-YunjianNeural",
                            "zh-CN-XiaoyiNeural",
                        ],
                        key="vid_voice",
                    )
                    voice_rate = st.select_slider(
                        "语速",
                        options=["-20%", "-10%", "+0%", "+10%", "+20%"],
                        value="+0%",
                        key="vid_voice_rate",
                    )
                    font_size = st.slider("字幕字号", 20, 60, 36, key="vid_font_size")
                with col2:
                    fps = st.selectbox("帧率", [24, 30, 60], index=0, key="vid_fps")
                    resolution = st.selectbox(
                        "分辨率",
                        ["原始", "1920x1080", "1280x720", "1080x1080"],
                        key="vid_res",
                    )
                    music_volume = st.slider("背景音乐音量", 0.0, 1.0, 0.3, 0.1, key="vid_music_vol")

                music_file = st.file_uploader("背景音乐（可选）", type=["mp3", "wav", "m4a"], key="vid_music")

                if st.button("生成专业版视频", key="btn_video_pro", type="primary"):
                    # 处理手动上传的脚本文件
                    if script_source == "手动上传" and script_file:
                        script_dir = Path("data/uploads/scripts")
                        script_dir.mkdir(parents=True, exist_ok=True)
                        script_path = str(script_dir / script_file.name)
                        with open(script_path, "wb") as f:
                            f.write(script_file.read())

                    music_path = None
                    if music_file:
                        music_dir = Path("data/uploads/music")
                        music_dir.mkdir(parents=True, exist_ok=True)
                        music_path = str(music_dir / music_file.name)
                        with open(music_path, "wb") as f:
                            f.write(music_file.read())

                    res = None if resolution == "原始" else resolution

                    with st.spinner("正在生成专业版视频（含TTS配音和字幕）..."):
                        gen = VideoGenerator()
                        result = gen.make_video_pro(
                            article_name=selected_video,
                            script_path=script_path,
                            voice=voice,
                            voice_rate=voice_rate,
                            music_path=music_path,
                            music_volume=music_volume,
                            font_size=font_size,
                            fps=fps,
                            resolution=res,
                        )

                    if result["status"] == "ok":
                        st.success("专业版视频生成完成！")
                        output = result["output"]
                        st.caption(f"输出路径: {output}")
                        if Path(output).exists():
                            with open(output, "rb") as f:
                                st.download_button(
                                    "下载视频",
                                    data=f.read(),
                                    file_name=f"{selected_video}_pro.mp4",
                                    mime="video/mp4",
                                )
                    else:
                        st.error(f"生成失败: {result['message']}")

            else:
                # 基础版
                col1, col2 = st.columns(2)
                with col1:
                    duration = st.slider("每张停留秒数", 1.0, 10.0, 3.0, 0.5, key="vid_dur")
                    fps = st.selectbox("帧率", [24, 30, 60], index=0, key="vid_fps")
                    resolution = st.selectbox(
                        "分辨率",
                        ["原始", "1920x1080", "1280x720", "1080x1080"],
                        key="vid_res",
                    )
                with col2:
                    transition = st.selectbox(
                        "转场效果",
                        ["fade", "none"],
                        format_func=lambda x: "淡入淡出" if x == "fade" else "无转场",
                        key="vid_trans",
                    )
                    title = st.text_input("片头标题（可选）", value=selected_video, key="vid_title")
                    music_file = st.file_uploader("背景音乐（可选）", type=["mp3", "wav", "m4a"], key="vid_music")

                if st.button("生成视频", key="btn_video", type="primary"):
                    music_path = None
                    if music_file:
                        music_dir = Path("data/uploads/music")
                        music_dir.mkdir(parents=True, exist_ok=True)
                        music_path = str(music_dir / music_file.name)
                        with open(music_path, "wb") as f:
                            f.write(music_file.read())

                    res = None if resolution == "原始" else resolution

                    with st.spinner("正在生成视频..."):
                        gen = VideoGenerator()
                        result = gen.make_video(
                            article_name=selected_video,
                            duration=duration,
                            fps=fps,
                            transition=transition,
                            music_path=music_path,
                            title=title if title.strip() else None,
                            resolution=res,
                        )

                    if result["status"] == "ok":
                        st.success("视频生成完成！")
                        output = result["output"]
                        st.caption(f"输出路径: {output}")
                        if Path(output).exists():
                            with open(output, "rb") as f:
                                st.download_button(
                                    "下载视频",
                                    data=f.read(),
                                    file_name=f"{selected_video}.mp4",
                                    mime="video/mp4",
                                )
                    else:
                        st.error(f"生成失败: {result['message']}")


if __name__ == "__main__":
    render_wechat_page()
