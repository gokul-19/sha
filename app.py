def main():
    # Theme selection
    if "theme" not in st.session_state:
        st.session_state.theme = "Light"
    theme = st.sidebar.selectbox("Theme", list(THEMES.keys()), index=0)
    st.session_state.theme = theme
    apply_theme(THEMES[theme])

    st.markdown('<div class="title">🎙️ Audio to Subtitles</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Convert your audio files to SRT subtitles</div>', unsafe_allow_html=True)

    # Sidebar features
    with st.sidebar:
        st.header("Options")
        confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.7)
        reduce_noise = st.checkbox("Reduce Background Noise", help="Apply basic noise reduction")

    # File uploader
    audio_file = st.file_uploader(
        "Upload Audio File",
        type=["mp3", "wav", "m4a"],
        help="Limit 200MB per file"
    )

    if audio_file:
        st.write(f"📄 **File:** {audio_file.name} ({audio_file.size / 1024:.1f}KB)")
        
        # Audio playback
        st.audio(audio_file, format=f"audio/{Path(audio_file.name).suffix[1:]}")

        # Settings
        col1, col2 = st.columns(2)
        with col1:
            model_size = st.selectbox("Model Size", ["tiny", "base", "small"], index=1)
        with col2:
            language = st.selectbox("Language", ["Auto-detect", "English", "Spanish"], index=0)

        # Transcribe button
        if st.button("Convert to Subtitles"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            with st.spinner("Processing audio..."):
                # Load audio directly to array
                status_text.text("Loading audio...")
                progress_bar.progress(10)
                audio_data, sr, tmp_path = load_audio_to_array(audio_file.read(), Path(audio_file.name).suffix, reduce_noise)
                if audio_data is None:
                    os.unlink(tmp_path)
                    return

                # Show waveform
                status_text.text("Generating waveform...")
                progress_bar.progress(30)
                waveform = generate_waveform(audio_data, sr)
                if waveform:
                    st.image(waveform, caption="Audio Waveform")

                # Transcribe directly with audio array
                status_text.text("Transcribing audio...")
                progress_bar.progress(50)
                model = load_model(model_size)
                lang = language if language != "Auto-detect" else None
                result = model.transcribe(audio_data, language=lang)
                
                # Filter by confidence
                status_text.text("Filtering transcription...")
                progress_bar.progress(70)
                segments = [seg for seg in result["segments"] if seg.get("confidence", 1.0) >= confidence_threshold]
                
                # Editable transcription
                status_text.text("Preparing results...")
                progress_bar.progress(90)
                edited_text = st.text_area("Edit Transcription", result["text"], height=200, key="edit_transcript")
                if edited_text != result["text"]:
                    # Update segments with edited text (simplified approach)
                    segments = [{"start": s["start"], "end": s["end"], "text": t.strip()} 
                               for s, t in zip(segments, edited_text.splitlines()) 
                               if t.strip()]

                # Generate SRT
                srt_path = generate_srt(segments, audio_file.name)

                # Display results
                progress_bar.progress(100)
                status_text.text("Done!")
                with st.container():
                    st.markdown('<div class="success-box">', unsafe_allow_html=True)
                    st.success("Conversion Complete!")
                    
                    tabs = st.tabs(["Text", "SRT Preview", "Download"])
                    
                    with tabs[0]:
                        st.text_area("Transcription", edited_text, height=200)
                    
                    with tabs[1]:
                        with open(srt_path, "r", encoding="utf-8") as f:
                            st.text_area("SRT Preview", f.read(), height=200)
                    
                    with tabs[2]:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            with open(srt_path, "rb") as f:
                                st.download_button(
                                    "Download SRT",
                                    f.read(),
                                    f"{Path(audio_file.name).stem}.srt",
                                    "text/plain"
                                )
                        with col2:
                            st.download_button(
                                "Download TXT",
                                edited_text.encode(),
                                f"{Path(audio_file.name).stem}.txt",
                                "text/plain"
                            )
                        with col3:
                            json_data = json.dumps({"text": edited_text, "segments": segments}, indent=2)
                            st.download_button(
                                "Download JSON",
                                json_data.encode(),
                                f"{Path(audio_file.name).stem}.json",
                                "application/json"
                            )
                    st.markdown('</div>', unsafe_allow_html=True)

                # Cleanup
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                if os.path.exists(srt_path):
                    os.unlink(srt_path)

    # External subtitle resource
    st.markdown(
        """
        <div style='text-align: center; margin-top: 30px; font-size: 0.95em; opacity: 0.8;'>
            Looking for existing subtitles? Check out 
            <a href="https://www.opensubtitles.org/en/subtitles/" target="_blank" style="color:#3498db; text-decoration: none; font-weight: 600;">
            OpenSubtitles.org</a>.
        </div>
        """,
        unsafe_allow_html=True
    )

    # Footer
    st.markdown("<footer style='text-align: center; padding: 20px;'>Made with Streamlit</footer>", unsafe_allow_html=True)
