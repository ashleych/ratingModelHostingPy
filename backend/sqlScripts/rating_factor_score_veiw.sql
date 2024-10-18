delete from lineitemvalue ;
select * from lineitemvalue l where line_item_meta_id ='cd798ed4-e74a-4484-a6c7-b3759d21d135' ;
--select * from lineitemmeta l where l."name" ='net_sales_manufacturing_sales';
CREATE VIEW v_rating_factor_scores AS
select
	rf.name AS rating_factor_name,
    rfs.raw_value_text,
    rfs.raw_value_float,
    rfs.score,
    rfs.score_dirty,
    rfs.rating_instance_id,
    rfs.rating_factor_id,
    rfs.id
FROM 
    ratingfactorscore rfs
JOIN 
    ratingfactor rf ON rfs.rating_factor_id = rf.id;
  
CREATE VIEW v_line_item_value AS
select
	l2.name AS line_item_name,
	l2.label AS line_item_label,
	l.id,
	l.financial_statement_id,
	l.value,
	l.created_at,
	l.updated_at
FROM 
    lineitemvalue l  
JOIN 
    lineitemmeta l2  on l.line_item_meta_id = l2.id;
    
drop view    v_line_item_value;
CREATE OR REPLACE VIEW v_line_item_value AS
SELECT
    l2.name AS line_item_name,
    l.value,
    l2.label AS line_item_label,
    l2.formula as formula,
    l2.lag_months as lag_months,
    fs.financials_period_year,
    fs.financials_period_month,
    l.id,
    l.financial_statement_id,
    l.created_at,
    l.updated_at
FROM
    lineitemvalue l
JOIN
    lineitemmeta l2 ON l.line_item_meta_id = l2.id
JOIN
    financialstatement fs ON l.financial_statement_id = fs.id;