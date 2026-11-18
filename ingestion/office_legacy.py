def extract_legacy_office(path) -> str:
    """Word 97 / PowerPoint 97 via installed Microsoft Office."""
    import pythoncom
    path = str(path)
    ext = path.lower().rsplit(".", 1)[-1]
    pythoncom.CoInitialize()
    try:
        import win32com.client
        if ext == "doc":
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(path, ReadOnly=True)
            text = doc.Content.Text
            doc.Close(False)
            word.Quit()
            return text or ""
        if ext == "ppt":
            ppt = win32com.client.DispatchEx("PowerPoint.Application")
            pres = ppt.Presentations.Open(path, WithWindow=False)
            parts = []
            for slide in pres.Slides:
                for shp in slide.Shapes:
                    if shp.HasTextFrame:
                        parts.append(shp.TextFrame.TextRange.Text)
            pres.Close()
            ppt.Quit()
            return "\n".join(parts)
    except Exception:
        return ""
    finally:
        pythoncom.CoUninitialize()
    return ""