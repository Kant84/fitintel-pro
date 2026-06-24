# fix_reports_endpoint.py
with open('app/api/v1/reports.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_csv = '''    elif request.format == "csv":
        # TODO: CSV export
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="CSV export not yet implemented",
        )'''

new_csv = '''    elif request.format == "csv":
        output = service.export_payments_csv(
            date_from=request.date_from,
            date_to=request.date_to,
            client_id=request.client_id,
            payment_direction=request.payment_direction,
            payment_category=request.payment_category,
            status=request.status,
        )
        
        filename = f"payments_report_{date.today().strftime('%Y%m%d')}.csv"
        
        return StreamingResponse(
            output,
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )'''

if old_csv in content:
    content = content.replace(old_csv, new_csv)
    with open('app/api/v1/reports.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Endpoint обновлен для CSV!")
else:
    print("Не найден блок CSV")
