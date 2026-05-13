ALTER TABLE public.usuarios
ADD COLUMN IF NOT EXISTS agencia_uri character varying(255);

COMMENT ON COLUMN public.usuarios.agencia_uri IS
'URI del individuo AgenciaViajes/PrestadorServicio al que pertenece un usuario Operador.';
