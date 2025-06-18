-- CreateTable
CREATE TABLE "Koella" (
    "id" SERIAL NOT NULL,
    "x" INTEGER NOT NULL,
    "Vo20" DOUBLE PRECISION NOT NULL,
    "glacier_area" INTEGER NOT NULL,
    "TB_start" INTEGER NOT NULL DEFAULT 30,
    "tol" INTEGER NOT NULL DEFAULT 5,
    "istep" INTEGER NOT NULL DEFAULT 5,
    "max_iter" INTEGER NOT NULL DEFAULT 1000,
    "project_id" TEXT NOT NULL,
    "koella_result_id" INTEGER,

    CONSTRAINT "Koella_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Koella_Result" (
    "id" SERIAL NOT NULL,
    "HQ" DOUBLE PRECISION NOT NULL,
    "Tc" DOUBLE PRECISION NOT NULL,
    "TB" DOUBLE PRECISION NOT NULL,
    "TFl" DOUBLE PRECISION NOT NULL,
    "FLeff" DOUBLE PRECISION NOT NULL,
    "i_final" DOUBLE PRECISION NOT NULL,
    "i_korrigiert" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "Koella_Result_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Koella_koella_result_id_key" ON "Koella"("koella_result_id");

-- AddForeignKey
ALTER TABLE "Koella" ADD CONSTRAINT "Koella_x_fkey" FOREIGN KEY ("x") REFERENCES "Annualities"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Koella" ADD CONSTRAINT "Koella_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "Project"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Koella" ADD CONSTRAINT "Koella_koella_result_id_fkey" FOREIGN KEY ("koella_result_id") REFERENCES "Koella_Result"("id") ON DELETE CASCADE ON UPDATE CASCADE;
