SELECT * FROM (
  VALUES
    ('CA', 'California'),
    ('NC', 'North Carolina'),
    ('NY', 'New York'),
    ('SC', 'South Carolina')
) AS states(state_code, state_name)
